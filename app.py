import asyncio
import os
import anthropic
from dotenv import load_dotenv
import streamlit as st
import streamlit.components.v1 as components

from chat_client import ChatClient
from detect import get_code_height, get_programming_language
from github_api import BranchDiff, fetch_git_diffs
from llm_client import LLMType, string_to_enum, get_available_models
from html_templates import (
    CODE_HIGHLIGHT_HTML_CONTENT,
    DIFF_VIEWER_HTML_CONTENT,
    MERMAID_HTML_CONTENT,
)
from db import (
    create_connection,
    db_init,
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
            width: 280px !important;
            background-color: #f8f9fa;
        }
        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem;
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
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

        /* Force left alignment for button content */
        section[data-testid="stSidebar"] div:nth-of-type(2) [data-testid="stHorizontalBlock"] [data-testid="column"] button div {
            justify-content: flex-start !important;
            text-align: left !important;
        }

        /* Individual button styling */
        section[data-testid="stSidebar"] div:nth-of-type(2) [data-testid="stHorizontalBlock"] [data-testid="column"] button {
            text-align: left !important;
            padding: 0.50rem 0rem !important;
            min-height: 0 !important;
            height: auto !important;
            margin: 0 !important;
            width: 100% !important;
            display: flex !important;
            justify-content: flex-start !important;
            border: 0px solid #e1e4e8 !important;
        }

        /* Remove extra spacing from column containers */
        section[data-testid="stSidebar"] div:nth-of-type(2) [data-testid="stHorizontalBlock"] > div {
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Reduce spacing between list items */
        section[data-testid="stSidebar"] div:nth-of-type(2) [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
            margin-top: -0.75rem !important;  /* Negative margin to pull items closer */
        }

        .compact-divider hr {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
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
        if st.button("✨ New Review", type="secondary", use_container_width=True):
            st.session_state.selected_review_id = None
            st.rerun()

        st.markdown("### Recent Reviews")

        # Reviews list
        for review in st.session_state.reviews:
            cols = st.columns([10])
            title = (
                review[4][:22] + "..."
                if review[4] and len(review[4]) > 22
                else (review[4] if review[4] else review[3])
            )

            if cols[0].button(
                f"📄 {title}", key=f"review-{review[0]}", use_container_width=True
            ):
                st.session_state.selected_review_id = review[0]
                st.rerun()


async def render_create_review_page(conn):
    with st.container():
        with st.expander("Create Review", expanded=True):
            col1, col2 = st.columns([5, 1.2])
            with col1:
                url_input = st.text_input(
                    "Enter a GitHub URL",
                    st.session_state.url_input,
                    placeholder="https://github.com/username/repo/pull/123",
                )
                st.caption("Supports: Pull Request URLs, Branch URLs, or Commit URLs")  # Added help text
            with col2:
                st.markdown('<div style="margin-top: 25px;"></div>', unsafe_allow_html=True)
                start_review = st.button("Review", type="primary", use_container_width=True)
            st.session_state.url_input = url_input

            # Two-column layout for template/model and prompt
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

                # Add model selection dropdown below template
                model_options = get_available_models()
                selected_model = st.selectbox(
                    "LLM Model",
                    model_options,
                    index=0,
                )

            with col2:
                prompt_input = st.text_area(
                    "Custom Instructions (Optional)", height=125
                )

            # Options in columns
            col1, col2 = st.columns(2)
            with col1:
                stream_checked = st.checkbox("Stream Output", True)
                per_file_checked = st.checkbox("Per File Analysis", True)
            with col2:
                whole_file_checked = st.checkbox("Analyze Whole File", False)
                ignore_tests_checked = st.checkbox("Ignore Tests", True)

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
                selected_model,
            )

            await process_review(
                diffs,
                per_file_checked,
                whole_file_checked,
                prompt_input,
                prompt_template_selected,
                selected_model,
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
    selected_model,
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
                    selected_model,
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

    # Modify the HTML content to include scrollbar styling directly
    html_content = f"""
        <style>
            ::-webkit-scrollbar {{
                width: 10px !important;
                height: 10px !important;
            }}
            ::-webkit-scrollbar-track {{
                background: transparent !important;
            }}
            ::-webkit-scrollbar-thumb {{
                background-color: rgba(49, 51, 63, 0.2) !important;
                border-radius: 5px !important;
                border: 2px solid transparent !important;
                background-clip: content-box !important;
            }}
            ::-webkit-scrollbar-thumb:hover {{
                background-color: rgba(49, 51, 63, 0.3) !important;
            }}
        </style>
        {DIFF_VIEWER_HTML_CONTENT(escaped_diff)}
    """
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

    # Modify the HTML content to include scrollbar styling directly
    html_content = f"""
        <style>
            ::-webkit-scrollbar {{
                width: 10px !important;
                height: 10px !important;
            }}
            ::-webkit-scrollbar-track {{
                background: transparent !important;
            }}
            ::-webkit-scrollbar-thumb {{
                background-color: rgba(49, 51, 63, 0.2) !important;
                border-radius: 5px !important;
                border: 2px solid transparent !important;
                background-clip: content-box !important;
            }}
            ::-webkit-scrollbar-thumb:hover {{
                background-color: rgba(49, 51, 63, 0.3) !important;
            }}
        </style>
        {CODE_HIGHLIGHT_HTML_CONTENT(language, code)}
    """
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
    selected_model,
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
        # Get the selected model and determine its type
        selected_model = selected_model or os.getenv("DEFAULT_LLM_MODEL")
        if "gpt" in selected_model.lower():
            client_type = LLMType.OPENAI
        elif "llama" in selected_model.lower():
            client_type = LLMType.OLLAMA
        elif "claude" in selected_model.lower():
            client_type = LLMType.CLAUDE
        else:
            client_type = string_to_enum(
                LLMType, os.getenv("DEFAULT_LLM_CLIENT", "openai")
            )

        chat = ChatClient(client_type, selected_model)

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

    # Wrap everything in an expander panel titled "Review"
    with st.expander("Review", expanded=True):
        # Review header with better layout
        hcol1, hcol2 = st.columns([19, 1])  # 80/20 split
        with hcol1:
            st.markdown(f"### {review[1]}")
        with hcol2:
            if st.button("🗑️", key=f"delete-{review[0]}", use_container_width=True):
                delete_review(conn, review[0])
                st.session_state.selected_review_id = None  # Reset to trigger new review screen
                st.rerun()
        # st.divider()
        st.markdown('<div class="compact-divider"><hr/></div>', unsafe_allow_html=True)

        # Review header
        st.markdown(
            f"""
            **GitHub URL:** [{review[2]}]({review[2]})  
            **Template:** {review[3] or 'Custom'}  
            **Model:** {review[7] if review[7] else 'N/A'}  
            **Prompt:** {review[4] if review[4] else 'None'}
        """
        )
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
        db_init(conn)
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
