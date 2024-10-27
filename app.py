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

# Set page configuration
st.set_page_config(
    page_title="Code Review AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better UI
st.markdown(
    """
    <style>
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            width: 300px !important;
            background-color: #f8f9fa;
        }
        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem;  /* Reduced from 1rem */
            padding-left: 1rem;
            padding-right: 1rem;
            padding-bottom: 1rem;
        }
        
        /* Add specific styling for sidebar header */
        section[data-testid="stSidebar"] h3:first-of-type {
            margin-top: 0;
            padding-top: 0;
        }
        
        /* Hide Streamlit branding */
        .stDeployButton {display:none;}
        footer {display:none;}
        
        /* Main content styling */
        .main > div {
            padding: 2em 2em;  /* Increased top padding from 1em to 2em */
        }
        
        /* Card-like containers */
        .stButton > button {
            border-radius: 4px;
            padding: 0.5rem 1rem;
        }
        
        /* Add new CSS for specific buttons */
        .small-button > button {
            width: auto !important;
        }
        
        /* Review items styling */
        .review-item {
            padding: 0.5rem;
            border-radius: 4px;
            margin-bottom: 0.5rem;
            background: white;
            border: 1px solid #e1e4e8;
        }
        
        /* Input fields styling */
        .stTextInput input {
            border-radius: 4px;
        }
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 4rem;
        }
        
        /* Headers */
        h1, h2, h3 {
            margin-bottom: 1rem;
        }
        
        /* Code containers */
        pre {
            padding: 1rem;
            border-radius: 4px;
            background-color: #f6f8fa;
        }
    </style>
""",
    unsafe_allow_html=True,
)


def init_session_state():
    # Remove the cache_data decorator
    if "url_input" not in st.session_state:
        st.session_state.url_input = ""
    if "selected_review_id" not in st.session_state:
        st.session_state.selected_review_id = None
    if "reviews" not in st.session_state:
        st.session_state.reviews = []
    if "has_run" not in st.session_state:
        st.session_state.has_run = False


async def render_sidebar(conn):
    with st.sidebar:
        st.markdown("### 🔍 Code Review AI")
        st.divider()

        # New Review Button
        if st.button("✨ New Review", type="primary", use_container_width=True):
            st.session_state.selected_review_id = None
            st.rerun()

        st.markdown("### Recent Reviews")

        # Reviews list
        for review in st.session_state.reviews:
            with st.container():
                cols = st.columns([8, 2])
                title = f"{review[4][:30]}" if review[4] else f"{review[3]}"

                if cols[0].button(
                    f"📄 {title}", key=f"review-{review[0]}", use_container_width=True
                ):
                    st.session_state.selected_review_id = review[0]
                    st.rerun()

                if cols[1].button("🗑️", key=f"delete-{review[0]}"):
                    delete_review(conn, review[0])
                    st.rerun()


async def render_create_review_page(conn):
    with st.container():
        # Create a visual container with a border and background
        with st.expander("Create New Review", expanded=True):
            # GitHub URL input
            url_input = st.text_input(
                "GitHub URL",
                st.session_state.url_input,
                placeholder="https://github.com/username/repo/pull/123",
            )
            st.session_state.url_input = url_input

            # Two-column layout for template and prompt
            col1, col2 = st.columns([1, 2])

            with col1:
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
                prompt_template_selected = st.selectbox(
                    "Review Template", prompt_template_options, index=0
                )

            with col2:
                prompt_input = st.text_area(
                    "Custom Instructions (Optional)", height=100
                )

            # Options in columns
            col1, col2 = st.columns(2)
            with col1:
                stream_checked = st.checkbox("Stream Output", True)
                per_file_checked = st.checkbox("Per File Analysis", True)
            with col2:
                whole_file_checked = st.checkbox("Analyze Whole File", False)
                ignore_tests_checked = st.checkbox("Ignore Tests", True)

            # Start Review button
            col1, _ = st.columns([2, 3])  # Adjusted ratio for button only
            start_review = False
            with col1:
                if st.button("Start Review", type="primary", use_container_width=False):
                    start_review = True

    # Process review outside of the panel
    if start_review:
        with st.spinner("Processing..."):
            diffs = fetch_git_diffs(url_input, ignore_tests=ignore_tests_checked)
            review_id = insert_review(
                conn,
                diffs.repo_name,
                url_input,
                prompt_template_selected,
                prompt_input,
            )

            await process_review(
                diffs,
                per_file_checked,
                whole_file_checked,
                prompt_input,
                prompt_template_selected,
                stream_checked,
                conn,
                review_id,
            )


async def process_review(
    diffs,
    per_file_checked,
    whole_file_checked,
    prompt_input,
    prompt_template_selected,
    stream_checked,
    conn,
    review_id,
):
    patches = diffs.patches if per_file_checked else ["\n".join(diffs.patches)]
    joined_filenames = " ".join(diffs.file_names)

    for idx, patch in enumerate(patches):
        file_name = diffs.file_names[idx] if per_file_checked else joined_filenames

        with st.expander(f"📁 {file_name}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                await render_code_view(
                    diffs, patch, file_name, per_file_checked, whole_file_checked, idx
                )
            with col2:
                await render_analysis(
                    diffs,
                    prompt_input,
                    prompt_template_selected,
                    stream_checked,
                    conn,
                    review_id,
                    file_name,
                    patch,
                    idx,
                    whole_file_checked,
                )


async def display_diff_with_diff2html(diff, per_file=True):
    """Render diff with syntax highlighting and better formatting."""
    height = min(get_code_height(diff), 1000) if per_file else get_code_height(diff)
    escaped_diff = diff.replace("`", "\\`").replace("${", "${'$'}{")

    # Add custom CSS for diff viewer
    st.markdown(
        """
        <style>
            .d2h-wrapper {
                border-radius: 4px;
                border: 1px solid #e1e4e8;
            }
            .d2h-file-header {
                padding: 0.5rem 1rem;
                background-color: #f6f8fa;
                border-bottom: 1px solid #e1e4e8;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    html_content = DIFF_VIEWER_HTML_CONTENT(escaped_diff)
    components.html(html_content, height=height, scrolling=True)


async def display_code_with_highlightjs(code, language, per_file=True):
    """Render code with syntax highlighting and better formatting."""
    height = min(get_code_height(code), 1000) if per_file else get_code_height(code)

    # Add custom CSS for code viewer
    st.markdown(
        """
        <style>
            pre code {
                border-radius: 4px;
                font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
            }
            .hljs {
                padding: 1rem !important;
                background-color: #f6f8fa !important;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    html_content = CODE_HIGHLIGHT_HTML_CONTENT(language, code)
    components.html(html_content, height=height, scrolling=True)


async def render_mermaid(mermaid_code):
    """Render Mermaid diagrams with better styling."""
    st.markdown(
        """
        <style>
            .mermaid {
                text-align: center;
                background-color: white;
                padding: 1rem;
                border-radius: 4px;
                border: 1px solid #e1e4e8;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    mermaid_template = MERMAID_HTML_CONTENT(mermaid_code)
    components.html(mermaid_template, height=1000)


async def process_stream(stream, client_type, output, key):
    """Process streaming responses with better error handling and UI feedback."""
    try:
        async for chunk in stream:
            content = ""
            if client_type == LLMType.OPENAI:
                content = chunk.choices[0].delta.content
            elif client_type == LLMType.OLLAMA:
                content = chunk["message"]["content"]
            elif client_type == LLMType.CLAUDE:
                if isinstance(chunk, anthropic.types.MessageStartEvent):
                    continue
                elif isinstance(chunk, anthropic.types.ContentBlockDeltaEvent):
                    content = chunk.delta.text if chunk.delta.text else ""
                elif isinstance(chunk, anthropic.types.MessageDeltaEvent):
                    if chunk.delta.stop_reason:
                        break
            else:
                raise ValueError(f"Unknown client type: {client_type}")

            if content:
                st.session_state[key] += content
                output.markdown(st.session_state[key])
    except Exception as e:
        st.error(f"Error processing stream: {str(e)}")
        raise


async def render_code_view(
    diffs, patch, file_name, per_file_checked, whole_file_checked, idx
):
    """Render code and diff views with tabs."""
    prog_language = get_programming_language("." + file_name.split(".")[-1])
    code = diffs.contents[idx] if whole_file_checked else patch

    if code[:4] == "diff":
        tabs = st.tabs(["✨ Diff View", "📄 Code View"])
        with tabs[0]:
            await display_diff_with_diff2html(code, per_file_checked)
        with tabs[1]:
            if per_file_checked:
                await display_code_with_highlightjs(
                    diffs.contents[idx], prog_language, per_file_checked
                )
            else:
                for i, content in enumerate(diffs.contents):
                    st.write(f"**{diffs.file_names[i]}**")
                    await display_code_with_highlightjs(
                        content, prog_language, per_file_checked
                    )
    else:
        await display_code_with_highlightjs(code, prog_language, per_file_checked)


async def render_analysis(
    diffs,
    prompt_input,
    prompt_template_selected,
    stream_checked,
    conn,
    review_id,
    file_name,
    patch,
    idx,
    whole_file_checked,
):
    """Render AI analysis with better formatting and error handling."""
    sys_out = st.empty()
    key = f"ai_comment_{idx}"
    st.session_state[key] = ""

    try:
        client_type = string_to_enum(LLMType, os.getenv("DEFAULT_LLM_CLIENT", "openai"))
        model_name = os.getenv(
            "DEFAULT_LLM_MODEL", get_default_llm_model_name(client_type)
        )
        chat = ChatClient(client_type, model_name)

        fpatch = (
            diffs.contents[idx]
            if whole_file_checked
            else (
                diffs.patches[idx] if isinstance(diffs.patches, list) else diffs.patches
            )
        )

        prompts = chat.prepare_prompts(prompt_input, prompt_template_selected, fpatch)

        if stream_checked:
            stream = await chat.async_chat_response(prompts)
            await process_stream(stream, client_type, sys_out, key)
            response = st.session_state[key]
        else:
            with st.spinner("Generating analysis..."):
                response = chat.chat_response(prompts)

        # Save analysis to database
        insert_file(conn, review_id, file_name, patch, diffs.contents[idx], response)

        # Render response
        await render_response(response, key, sys_out)

    except Exception as e:
        st.error(f"Error during analysis: {str(e)}")
        raise


async def render_response(content, key, sys_out):
    """Render AI response with better formatting."""
    sys_out.empty()

    if content.startswith("```mermaid"):
        tabs = st.tabs(["📊 Diagram", "📝 Source"])
        with tabs[0]:
            mermaid_code = content[10:-3]
            st.session_state[key] = await render_mermaid(mermaid_code)
            if st.session_state[key]:
                tabs[0].write(st.session_state[key])
        with tabs[1]:
            st.session_state[key] = content
            tabs[1].code(content, language="mermaid")
    else:
        st.session_state[key] = content
        sys_out.markdown(st.session_state[key])


async def render_view_review_page(conn):
    """Render saved review with better layout and formatting."""
    review, files = get_review_with_files(conn, st.session_state.selected_review_id)

    if not review:
        st.error("Review not found!")
        return

    # Review header
    st.markdown(
        f"""
        ### {review[1]}
        **GitHub URL:** [{review[2]}]({review[2]})  
        **Template:** {review[3] or 'Custom'}  
        **Prompt:** {review[4] if review[4] else 'None'}
    """
    )

    st.divider()

    # Process files
    filenames = [f[2] for f in files]
    patches = [f[3] for f in files]
    contents = [f[4] for f in files]
    responses = [f[5] for f in files]

    diffs = BranchDiff(review[1], None, None, filenames, patches, contents)

    for idx, (patch, response) in enumerate(zip(patches, responses)):
        with st.expander(f"📁 {filenames[idx]}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                await render_code_view(diffs, patch, filenames[idx], True, False, idx)
            with col2:
                sys_out = col2.empty()
                key = f"ai_comment_{idx}"
                await render_response(response, key, sys_out)


async def main():
    # Initialize session state at the start of main
    init_session_state()

    conn = create_connection("bin/code_reviews.db")
    if conn is None:
        st.error("Database connection failed!")
        return

    if not st.session_state.has_run:
        create_tables(conn)
        st.session_state.has_run = True

    if st.session_state.selected_review_id is None:
        st.session_state.selected_review_id = None

    st.session_state.reviews = get_all_reviews(conn)

    await render_sidebar(conn)

    if st.session_state.selected_review_id:
        await render_view_review_page(conn)
    else:
        await render_create_review_page(conn)

    if conn:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())

