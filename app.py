import asyncio
import os
from dotenv import load_dotenv
import streamlit as st

from ask_diff import ask_diff
from llm_client import LLMType, get_default_llm_model_name, string_to_enum


load_dotenv()


def remove_backticks(text):
    if text.startswith("```") and text.endswith("```"):
        return text[3:-3]
    else:
        return text


async def main():
    st.set_page_config(layout="wide")
    st.markdown("""
        <style>
            .stDeployButton {display:none;}
        </style>
    """, unsafe_allow_html=True)

    github_url_input = st.text_input("Github Url:", "")

    prompt_template_options = ["code-review", "code-summary", 'pr-description', "code-debate", "code-smells",
                               "code-refactor", "code-checklist", "code-review-verbose", None]
    prompt_template_selected_option = st.selectbox("Prompt template:", prompt_template_options)

    prompt_input = st.text_area("Prompt: (Optional)")

    stream_checkbox = st.checkbox("Stream", True)
    per_file_checkbox = st.checkbox("Per File", True)
    whole_file_checkbox = st.checkbox("Whole File", False)

    # Button
    button_clicked = st.button("Get Review")

    client_type = string_to_enum(LLMType, os.getenv('DEFAULT_LLM_CLIENT', "openai"))
    model_name = os.getenv('DEFAULT_LLM_MODEL', get_default_llm_model_name(client_type))
    print("\nClient:", client_type.name.lower(), ", Model:", model_name)

    # Button
    if button_clicked:
        resp = await ask_diff(
            github_url_input,
            client_type,
            model_name,
            prompt_input,
            prompt_template_selected_option,
            stream=stream_checkbox,
            per_file=per_file_checkbox,
            whole_file=whole_file_checkbox,
        )
        for item in resp:
                # Create two columns for each item
                col1, col2 = st.columns([2, 2])

                # Display message in the first column
                message = remove_backticks(item.message)
                with col1:
                    st.write(f"**{item.file_name}**")
                    st.code(message, language="")

                # Display response in the second column
                with col2:
                    st.write(f"**{item.file_name}**")
                    st.write(item.response)


if __name__ == "__main__":
    asyncio.run(main())
