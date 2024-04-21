import asyncio
import os
from dotenv import load_dotenv
import streamlit as st

from ask_diff import ask_diff
from detect import get_programming_language
from github_api import fetch_git_diffs
from llm_client import LLMType, get_default_llm_model_name, string_to_enum


load_dotenv()

st.set_page_config(layout="wide")


# Define a function to initialize session state
@st.cache_data(persist="disk")
def init_session_state():
    return {"url_input": ""}

# Initialize session state
st.session_state = init_session_state()

async def main():
    st.markdown("""
        <style>
            .stDeployButton {display:none;}
        </style>
    """, unsafe_allow_html=True)

    url_input = st.text_input("Github Url:", st.session_state["url_input"])
    # Save the value to session state
    st.session_state["user_input"] = url_input

    prompt_template_options = ["code-review", "code-summary", 'pr-description', "code-debate", "code-smells",
                               "code-refactor", "code-checklist", "code-review-verbose", 'explain-lines',
                               'explain-lines-verbose', 'doc-strings', 'doc-markdown', None]
    prompt_template_selected_option = st.selectbox("Prompt template:", prompt_template_options)
    prompt_input = st.text_area("Prompt: (Optional)", None)

    stream_checkbox = st.checkbox("Stream", True)
    per_file_checkbox = st.checkbox("Per File", True)
    whole_file_checkbox = st.checkbox("Whole File", False)

    button_clicked = st.button("Get Review")

    client_type = string_to_enum(LLMType, os.getenv('DEFAULT_LLM_CLIENT', "openai"))
    model_name = os.getenv('DEFAULT_LLM_MODEL', get_default_llm_model_name(client_type))
    # print("\nClient:", client_type.name.lower(), ", Model:", model_name)

    if button_clicked:
        diffs = fetch_git_diffs(url_input)
        patches = diffs.patches if per_file_checkbox else ["\n".join(diffs.patches)]
        joined_filenames = " ".join(diffs.file_names)
        for idx, patch in enumerate(patches):
            file_name = diffs.file_names[idx] if per_file_checkbox else joined_filenames
            prog_language = get_programming_language("." +  diffs.file_names[idx].split(".")[-1])
            col1, col2 = st.columns([2, 2])
            code = diffs.contents[idx] if whole_file_checkbox else patch
            with col1:
                st.write(f"**{file_name}**")
                if whole_file_checkbox:
                    st.code(code, language=prog_language, line_numbers=True)
                else:
                    st.code(code, language=prog_language, line_numbers=False)

            with col2:
                st.write(f"**{file_name}**")
                sys_out = col2.empty()
                key = f"ai_comment_{idx}"
                if key not in st.session_state:
                    st.session_state[key] = "Loading AI comments..."
                    patch = diffs.contents[idx] if whole_file_checkbox else diffs.patches[idx]
                    await ask_diff(patch, client_type, model_name, sys_out, prompt_input, prompt_template_selected_option,
                        False, stream_checkbox)


if __name__ == "__main__":
    asyncio.run(main())
