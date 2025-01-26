from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import streamlit as st
from lemma.views.config import ReviewConfig, DiffData
from lemma.llm_client import get_available_models


@dataclass
class ReviewFormInputs:
    """User inputs from the review form."""

    url: str
    prompt_template: Optional[str]
    model: str
    custom_instructions: str
    stream_output: bool
    per_file_analysis: bool
    analyze_whole_file: bool
    ignore_tests: bool


@dataclass
class FormOptions:
    """Available options for form fields."""

    prompt_templates: List[Optional[str]] = field(
        default_factory=lambda: [
            "code-review",
            "code-summary",
            "dependency-order",
            "review-by-context",
            "code-debate",
            "code-smells",
            "code-refactor",
            "explain-lines",
            "doc-strings",
            "doc-markdown",
            "unit-test",
            None,
        ]
    )
    models: List[str] = field(default_factory=get_available_models)


def create_review_form() -> ReviewFormInputs:
    """Create and render the review form."""
    url_input = st.text_input(
        "Enter a GitHub URL",
        st.session_state.url_input,
        placeholder="https://github.com/username/repo/pull/123",
    )
    st.caption("Supports: Pull Request URLs, Branch URLs, or Commit URLs")
    st.session_state.url_input = url_input

    col1, col2 = st.columns([1, 2])
    form_options = FormOptions()

    with col1:
        prompt_template = st.selectbox(
            "Review Template", form_options.prompt_templates, index=0
        )
        model = st.selectbox(
            "LLM Model",
            form_options.models,
            index=0,
        )

    with col2:
        custom_instructions = st.text_area("Custom Instructions (Optional)", height=125)

    col1, col2 = st.columns(2)
    with col1:
        stream_output = st.checkbox("Stream Output", True)
        per_file_analysis = st.checkbox("Per File Analysis", False)
    with col2:
        analyze_whole_file = st.checkbox("Analyze Whole File", False)
        ignore_tests = st.checkbox("Ignore Tests", True)

    return ReviewFormInputs(
        url=url_input,
        prompt_template=prompt_template,
        model=model,
        custom_instructions=custom_instructions,
        stream_output=stream_output,
        per_file_analysis=per_file_analysis,
        analyze_whole_file=analyze_whole_file,
        ignore_tests=ignore_tests,
    )


def create_review_config(
    form_inputs: ReviewFormInputs, diffs: DiffData
) -> ReviewConfig:
    """Create a review configuration from form inputs."""
    return ReviewConfig(
        per_file_analysis=form_inputs.per_file_analysis,
        analyze_whole_file=form_inputs.analyze_whole_file,
        prompt_input=form_inputs.custom_instructions,
        prompt_template_selected=form_inputs.prompt_template,
        selected_model=form_inputs.model,
        stream_checked=form_inputs.stream_output,
        repo_name=diffs.repo_name,
        url=form_inputs.url,
        created_at=datetime.now(),
    )
