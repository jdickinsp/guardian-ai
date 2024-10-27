import asyncio
import os
import anthropic
from dotenv import load_dotenv
import streamlit as st
import streamlit.components.v1 as components

from chat_client import ChatClient
from detect import get_code_height, get_programming_language
from github_api import BranchDiff, fetch_git_diffs
from llm_client import LLMType, get_default_llm_model_name, string_to_enum
from html_templates import (
    CODE_HIGHLIGHT_HTML_CONTENT,
    DIFF_VIEWER_HTML_CONTENT,
    MERMAID_HTML_CONTENT,
)
from db import (
    create_connection,
    create_tables,
    delete_review,
    get_all_reviews,
    get_review_with_files,
    insert_file,
    insert_review,
)


load_dotenv()

st.set_page_config(layout="wide")


# Define a function to initialize session state
@st.cache_data(persist="disk")
def init_session_state():
    return {"url_input": "", "selected_review_id": None}


# Initialize session state
st.session_state.update(init_session_state())


def display_diff_with_diff2html(diff, per_file=True):
    height = get_code_height(diff)
    if per_file is True:
        height = min(height, 1000)
    escaped_diff = diff.replace("`", "\\`").replace("${", "${'$'}{")
    html_content = DIFF_VIEWER_HTML_CONTENT(escaped_diff)
    components.html(html_content, height=height, scrolling=True)


def display_code_with_highlightjs(code, language, per_file=True):
    height = get_code_height(code)
    if per_file is True:
        height = min(height, 1000)
    html_content = CODE_HIGHLIGHT_HTML_CONTENT(language, code)
    components.html(html_content, height=height, scrolling=True)


def render_mermaid(mermaid_code):
    # Mermaid diagram template
    mermaid_template = MERMAID_HTML_CONTENT(mermaid_code)
    # Render the Mermaid diagram in Streamlit
    components.html(mermaid_template, height=1000)


async def process_stream(stream, client_type, output, key):
    async for chunk in stream:
        content = ""
        if client_type == LLMType.OPENAI:
            content = chunk.choices[0].delta.content
        elif client_type == LLMType.OLLAMA:
            content = chunk["message"]["content"]
        elif client_type == LLMType.CLAUDE:
            if isinstance(chunk, anthropic.types.MessageStartEvent):
                continue  # Skip the start event
            elif isinstance(chunk, anthropic.types.ContentBlockDeltaEvent):
                if chunk.delta.text:
                    content = chunk.delta.text
            elif isinstance(chunk, anthropic.types.MessageDeltaEvent):
                if chunk.delta.stop_reason:
                    break  # End of message
        else:
            raise Exception("unknown client_type")
        if content:
            st.session_state[key] += content
            output.write(st.session_state[key])


async def render_diff_and_code(
    code, file_name, per_file_checked, prog_language, diffs, idx
):
    st.write(f"**{file_name}**")
    if code[:4] == "diff":
        tab1, tab2 = st.tabs(["✨ Diff", "📄 Code"])
        with tab1:
            display_diff_with_diff2html(code, per_file_checked)
        with tab2:
            if per_file_checked:
                display_code_with_highlightjs(
                    diffs.contents[idx], prog_language, per_file_checked
                )
            else:
                for i, content in enumerate(diffs.contents):
                    tab2.write(f"**{diffs.file_names[i]}**")
                    display_code_with_highlightjs(
                        content, prog_language, per_file_checked
                    )
    else:
        tab1 = st.tabs(["📄 Code"])
        display_code_with_highlightjs(code, prog_language, per_file_checked)


async def render_response(content, key, sys_out):
    sys_out.empty()
    if content.startswith("```mermaid"):
        tab1, tab2 = st.tabs(["Render", "Code"])
        mermaid_code = content[10:-3]
        with tab1:
            st.session_state[key] = render_mermaid(mermaid_code)
            if st.session_state[key]:
                tab1.write(st.session_state[key])
        with tab2:
            st.session_state[key] = content
            tab2.write(st.session_state[key])
    else:
        st.session_state[key] = content
        sys_out.write(st.session_state[key])


async def render_sidebar(conn):
    header_container = st.sidebar.container(border=True)
    with header_container:
        left_side, _, right_side = header_container.columns([5, 6, 5], gap="small")
        with left_side:
            left_side.write("## Reviews")
        with right_side:
            if right_side.button(
                "📝", key="new_review", type="primary", use_container_width=True
            ):
                st.session_state["selected_review_id"] = None

    for review in st.session_state["reviews"]:
        if review[4]:
            title = f"{review[4][:30]}"
        else:
            title = f"{review[3]}"
        sidebar_container = st.sidebar.container()
        with sidebar_container:
            col1, col2 = st.columns([9, 1], gap="small")
            with col1:
                review_button_clicked = col1.button(
                    f"{title}: {review[1]}", key=f"review-{review[0]}"
                )
                if review_button_clicked:
                    st.session_state["selected_review_id"] = review[0]
            with col2:
                review_options_clicked = col2.button(
                    "x", key=f"review-options-{review[0]}"
                )
                if review_options_clicked:
                    delete_review(conn, review[0])
                    st.rerun()  # Ensure the UI is refreshed


async def render_create_review_page(conn):
    url_input = st.text_input("Github Url:", st.session_state["url_input"])
    # Save the value to session state
    st.session_state["url_input"] = url_input

    prompt_template_options = [
        "code-review",
        "code-summary",
        "code-debate",
        "code-smells",
        "code-refactor",
        "explain-lines",
        "doc-strings",
        "doc-markdown",
        "unit-test",
        None,
    ]
    prompt_template_selected = st.selectbox("Prompt template:", prompt_template_options)
    prompt_input = st.text_area("Prompt: (Optional)", None)

    stream_checked = st.checkbox("Stream Output", True)
    per_file_checked = st.checkbox("Per File Analysis", True)
    whole_file_checked = st.checkbox("Analyze The Whole File", False)
    ignore_tests_checked = st.checkbox("Ignore Tests In Review", True)

    button_clicked = st.button("Get Response", type="primary")

    client_type = string_to_enum(LLMType, os.getenv("DEFAULT_LLM_CLIENT", "openai"))
    model_name = os.getenv("DEFAULT_LLM_MODEL", get_default_llm_model_name(client_type))
    chat = ChatClient(client_type, model_name)

    if button_clicked:
        fetchingholder = st.empty().text("Fetching...")
        diffs = fetch_git_diffs(url_input, ignore_tests=ignore_tests_checked)
        # save review
        review_id = insert_review(
            conn, diffs.repo_name, url_input, prompt_template_selected, prompt_input
        )
        fetchingholder.empty()
        patches = diffs.patches if per_file_checked else ["\n".join(diffs.patches)]
        joined_filenames = " ".join(diffs.file_names)
        for idx, patch in enumerate(patches):
            file_name = diffs.file_names[idx] if per_file_checked else joined_filenames
            prog_language = get_programming_language(
                "." + diffs.file_names[idx].split(".")[-1]
            )
            col1, col2 = st.columns([2, 2])
            code = diffs.contents[idx] if whole_file_checked else patch
            with col1:
                await render_diff_and_code(
                    code, file_name, per_file_checked, prog_language, diffs, idx
                )
            with col2:
                st.write(f"**{file_name}**")
                sys_out = col2.empty()
                key = f"ai_comment_{idx}"
                st.session_state[key] = ""
                if per_file_checked:
                    fpatch = (
                        diffs.contents[idx]
                        if whole_file_checked
                        else diffs.patches[idx]
                    )
                else:
                    fpatch = (
                        " ".join(diffs.contents)
                        if whole_file_checked
                        else " ".join(diffs.patches)
                    )
                prompts = chat.prepare_prompts(
                    prompt_input, prompt_template_selected, fpatch
                )
                if stream_checked:
                    stream = await chat.async_chat_response(prompts)
                    await process_stream(stream, client_type, sys_out, key)
                    response = st.session_state[key]
                    insert_file(
                        conn, review_id, file_name, patch, diffs.contents[idx], response
                    )
                    await render_response(response, key, sys_out)
                else:
                    placeholder = col2.empty().text("Processing...")
                    response = chat.chat_response(prompts)
                    insert_file(
                        conn, review_id, file_name, patch, diffs.contents[idx], response
                    )
                    placeholder.empty()
                    await render_response(response, key, sys_out)


async def render_view_review_page(conn):
    review, files = get_review_with_files(conn, st.session_state["selected_review_id"])
    whole_file_checked = False
    per_file_checked = True
    if review:
        st.header("Review Details")
        st.write(f"**Name:** {review[1]}")
        st.write(f"**GitHub URL:** {review[2]}")
        st.write(f"**Prompt Template:** {review[3]}")
        st.write(f"**Prompt:** {review[4]}")

    filenames = [f[2] for f in files]
    patches = [f[3] for f in files]
    contents = [f[4] for f in files]
    responses = [f[5] for f in files]
    diffs = BranchDiff(review[1], None, None, filenames, patches, contents)
    patches = diffs.patches if per_file_checked else ["\n".join(diffs.patches)]
    joined_filenames = " ".join(diffs.file_names)
    for idx, patch in enumerate(patches):
        file_name = diffs.file_names[idx] if per_file_checked else joined_filenames
        prog_language = get_programming_language(
            "." + diffs.file_names[idx].split(".")[-1]
        )
        col1, col2 = st.columns([2, 2])
        code = diffs.contents[idx] if whole_file_checked else patch
        with col1:
            await render_diff_and_code(
                code, file_name, per_file_checked, prog_language, diffs, idx
            )
        with col2:
            st.write(f"**{file_name}**")
            sys_out = col2.empty()
            key = f"ai_comment_{idx}"
            if key not in st.session_state:
                st.session_state[key] = ""
            content = responses[idx]
            await render_response(content, key, sys_out)


async def main():
    st.markdown(
        """
        <style>
            .stDeployButton {display:none;}
            /* Reduce the width of the sidebar */
            section[data-testid="stSidebar"] {
                width: 200px !important; # Set the width to your desired value
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Create a connection to the SQLite database
    database = "bin/code_reviews.db"
    conn = create_connection(database)
    if conn is None:
        st.error("Error! Cannot create the database connection.")

    # Initialize session state flag if it doesn't exist
    if "has_run" not in st.session_state:
        # print('has_run not in state, setting to False')
        st.session_state["has_run"] = False

    # Check the flag and run the function if it hasn't run yet
    if not st.session_state["has_run"]:
        # print('has_run is False, running function')
        create_tables(conn)
        st.session_state["has_run"] = True
    else:
        print("has_run is True, function will not run")

    # Initialize selected review ID and reviews list
    if "selected_review_id" not in st.session_state:
        st.session_state["selected_review_id"] = None

    st.session_state["reviews"] = get_all_reviews(conn)

    await render_sidebar(conn)  # Render the sidebar with the updated reviews

    if not st.session_state["selected_review_id"]:
        await render_create_review_page(conn)  # Render the create review page

    if st.session_state["selected_review_id"]:
        await render_view_review_page(conn)  # Render the view review page

    # Close the database connection
    if conn:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
