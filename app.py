import asyncio
import os
from dotenv import load_dotenv
import streamlit as st
import streamlit.components.v1 as components

from ask_diff import ask_diff
from detect import get_programming_language
from github_api import fetch_git_diffs
from llm_client import LLMType, get_default_llm_model_name, string_to_enum
from html_templates import CODE_HIGHLIGHT_HTML_CONTENT, DIFF_VIEWER_HTML_CONTENT


load_dotenv()

st.set_page_config(layout="wide")


# Define a function to initialize session state
@st.cache_data(persist="disk")
def init_session_state():
    return {"url_input": ""}

# Initialize session state
st.session_state = init_session_state()


def display_diff_with_diff2html(diff):
    escaped_diff = diff.replace("`", "\\`").replace("${", "${'$'}{")
    html_content = DIFF_VIEWER_HTML_CONTENT(escaped_diff)
    components.html(html_content, height=800, scrolling=True)


def display_code_with_highlightjs(code, language):
    html_content = CODE_HIGHLIGHT_HTML_CONTENT(language, code)
    components.html(html_content, height=800, scrolling=True)


async def main():
    st.markdown("""
        <style>
            .stDeployButton {display:none;}
        </style>
    """, unsafe_allow_html=True)

    url_input = st.text_input("Github Url:", st.session_state["url_input"])
    # Save the value to session state
    st.session_state["user_input"] = url_input

    prompt_template_options = ["code-review", "code-summary", "code-debate", 
                               "code-smells", "code-refactor", 'explain-lines',
                               'doc-strings', 'doc-markdown', 'unit-test', None]
    prompt_template_selected = st.selectbox("Prompt template:", prompt_template_options)
    prompt_input = st.text_area("Prompt: (Optional)", None)

    stream_checked = st.checkbox("Stream", True)
    per_file_checked = st.checkbox("Per File", True)
    whole_file_checked = st.checkbox("Whole File", False)

    button_clicked = st.button("Get Response")

    client_type = string_to_enum(LLMType, os.getenv('DEFAULT_LLM_CLIENT', "openai"))
    model_name = os.getenv('DEFAULT_LLM_MODEL', get_default_llm_model_name(client_type))

    if button_clicked:
        fetchingholder = st.empty().text('Fetching...')
        diffs = fetch_git_diffs(url_input)
        fetchingholder.empty()
        patches = diffs.patches if per_file_checked else ["\n".join(diffs.patches)]
        joined_filenames = " ".join(diffs.file_names)
        for idx, patch in enumerate(patches):
            file_name = diffs.file_names[idx] if per_file_checked else joined_filenames
            prog_language = get_programming_language("." +  diffs.file_names[idx].split(".")[-1])
            col1, col2 = st.columns([2, 2])
            code = diffs.contents[idx] if whole_file_checked else patch
            with col1:
                st.write(f"**{file_name}**")
                if code[:4] == 'diff':
                    tab1, tab2 = st.tabs(["✨ Diff", "📄 Code"])
                    with tab1:
                        display_diff_with_diff2html(code)
                    with tab2:
                        display_code_with_highlightjs(diffs.contents[idx], prog_language)
                else:
                    tab1 = st.tabs(["📄 Code"])
                    display_code_with_highlightjs(code, prog_language)

            with col2:
                st.write(f"**{file_name}**")
                tab1, tab2 = st.tabs(["📝 Response", "💬 Chat"])
                with tab1:
                    sys_out = col2.empty()
                    key = f"ai_comment_{idx}"
                    if key not in st.session_state:
                        st.session_state[key] = "Loading AI comments..."
                        patch = diffs.contents[idx] if whole_file_checked else diffs.patches[idx]
                        placeholder = st.empty().text('Processing...') if not stream_checked else None
                        await ask_diff(patch, client_type, model_name, sys_out, prompt_input, prompt_template_selected,
                                False, stream_checked)
                        if placeholder:
                            placeholder.empty()
                with tab2:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
