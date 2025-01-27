from datetime import datetime
from typing import Any, List, Tuple

import streamlit as st
import streamlit.components.v1 as components
from db import (
    delete_review,
    get_all_project_reviews,
    get_all_projects,
    get_all_reviews,
    get_review_with_files,
    insert_review,
)
from detect import get_code_height, get_programming_language
from github_api import (
    BranchDiff,
    fetch_git_diffs,
    get_github_url_type,
    validate_github_repo_url,
)

from lemma.views.config import (
    AnalysisContext,
    DiffData,
    ModelConfig,
    Project,
    ReviewConfig,
)
from lemma.views.forms import FormOptions, ReviewFormInputs
from lemma.views.html_templates import (
    CODE_HIGHLIGHT_HTML_CONTENT,
    DIFF_VIEWER_HTML_CONTENT,
    MERMAID_HTML_CONTENT,
)
from lemma.views.processing import (
    generate_analysis,
    get_patches,
    save_project,
    save_review,
)


async def process_review(
    diffs: DiffData, config: ReviewConfig, conn: Any, review_id: str
) -> None:
    """Process code review for either individual files or combined patches."""
    patches, filenames = get_patches(diffs, config.per_file_analysis)

    for idx, (patch, file_name) in enumerate(zip(patches, filenames)):
        await render_patch_section(
            diffs, config, conn, review_id, file_name, patch, idx
        )


async def render_code_view(
    diffs: DiffData, patch: str, file_name: str, config: ReviewConfig, idx: int
):
    """Render code and diff views with tabs."""
    if config is None:
        config = ReviewConfig()

    prog_language = get_programming_language("." + file_name.split(".")[-1])
    code = diffs.contents[idx] if config.analyze_whole_file else patch

    if code[:4] == "diff":
        tabs = st.tabs(["✨ Diff View", "📄 Code View"])
        with tabs[0]:
            await display_diff_with_diff2html(code, config.per_file_analysis)
        with tabs[1]:
            if config.per_file_analysis:
                await display_code_with_highlightjs(
                    diffs.contents[idx], prog_language, config.per_file_analysis
                )
            else:
                for i, content in enumerate(diffs.contents):
                    st.write(f"**{diffs.file_names[i]}**")
                    await display_code_with_highlightjs(
                        content, prog_language, config.per_file_analysis
                    )
    else:
        await display_code_with_highlightjs(
            code, prog_language, config.per_file_analysis
        )


async def display_diff_with_diff2html(diff: str, per_file: bool = True):
    """Render diff with syntax highlighting."""
    height = min(get_code_height(diff), 1000) if per_file else get_code_height(diff)
    escaped_diff = diff.replace("`", "\\`").replace("${", "${'$'}{")

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

    html_content = format_html_with_scrollbars(DIFF_VIEWER_HTML_CONTENT(escaped_diff))
    components.html(html_content, height=height, scrolling=True)


async def display_code_with_highlightjs(
    code: str, language: str, per_file: bool = True
):
    """Render code with syntax highlighting."""
    height = min(get_code_height(code), 1000) if per_file else get_code_height(code)

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

    html_content = format_html_with_scrollbars(
        CODE_HIGHLIGHT_HTML_CONTENT(language, code)
    )
    components.html(html_content, height=height, scrolling=True)


async def render_mermaid(mermaid_code: str):
    """Render Mermaid diagrams."""
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


def format_html_with_scrollbars(content: str) -> str:
    """Add custom scrollbar styling to HTML content."""
    return f"""
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
        {content}
    """


def get_review_title(review):
    limit = 14
    github_url = review["github_url"]
    github_url_type = review["github_url_type"]
    prompt_template = review["prompt_template"]
    prompt = review["prompt"]
    if github_url_type:
        if github_url_type == "file_path":
            return prompt_template + " " + github_url.split("/")[-1][:limit]
        elif github_url_type == "folder_path":
            return prompt_template + " /" + github_url.split("/")[-1][:limit]
        elif github_url_type == "branch":
            return prompt_template + " " + github_url.split("/")[-1][:limit]
        elif github_url_type == "pull_request":
            return prompt_template + " pull/" + github_url.split("/")[-1][:limit]
        elif github_url_type == "commit":
            return prompt_template + " " + github_url.split("/")[-1][:7]
    title = (
        prompt[:26] + "..."
        if prompt and len(prompt) > 26
        else (prompt if prompt else prompt_template)
    )
    return title


async def render_sidebar(conn):
    st.session_state.reviews = get_all_reviews(conn)
    with st.sidebar:
        st.markdown("### 🔍 Lemma")

        if st.button("✨ New Review", type="secondary", use_container_width=True):
            st.session_state.selected_review_id = None
            st.session_state.current_view = "home"
            st.rerun()

        if st.button("📁 Projects", type="secondary", use_container_width=True):
            st.session_state.selected_review_id = None
            st.session_state.current_view = "projects"
            st.rerun()

        st.divider()
        st.markdown("### Recent Reviews")

        # Reviews list
        for review in st.session_state.reviews:
            cols = st.columns([10])
            title = get_review_title(review)
            if cols[0].button(
                f"{title}", key=f"review-{review['id']}", use_container_width=True
            ):
                st.session_state.selected_review_id = review["id"]
                st.session_state.current_view = "review"
                st.rerun()


def create_review_form() -> ReviewFormInputs:
    """Create and render the review form, returning the form inputs."""
    url_input = st.text_input(
        "Enter a GitHub URL",
        st.session_state.url_input,
        placeholder="https://github.com/username/repo/pull/123",
    )
    st.caption("Supports: Pull Request URLs, Branch URLs, or Commit URLs")
    st.session_state.url_input = url_input

    # Two-column layout for template/model and prompt
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

    # Options in columns
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
    form_inputs: ReviewFormInputs, diffs: DiffData, project_id=None
) -> ReviewConfig:
    """Create a review configuration from form inputs."""
    url_type = get_github_url_type(diffs)
    return ReviewConfig(
        # Processing configuration
        per_file_analysis=form_inputs.per_file_analysis,
        analyze_whole_file=form_inputs.analyze_whole_file,
        prompt_input=form_inputs.custom_instructions,
        prompt_template_selected=form_inputs.prompt_template,
        selected_model=form_inputs.model,
        stream_checked=form_inputs.stream_output,
        # Metadata
        review_id=None,
        repo_name=diffs.repo_name,
        url=form_inputs.url,
        url_type=url_type,
        created_at=datetime.now(),
        project_id=project_id,
    )


async def render_create_review_page(conn, project_id=None):
    """Render the create review page and handle form submission."""
    with st.container():
        title = f"Create Review - {project_id}" if project_id else "Create Review"
        with st.expander(title, expanded=True):
            col1, col2 = st.columns([5, 1.2])

            with col1:
                form_inputs = create_review_form()

            with col2:
                st.markdown(
                    '<div style="margin-top: 25px;"></div>', unsafe_allow_html=True
                )
                start_review = st.button(
                    "Review", type="primary", use_container_width=True
                )

    # Process review outside of the panel
    if start_review:
        with st.spinner("Processing..."):
            diffs = fetch_git_diffs(
                form_inputs.url, ignore_tests=form_inputs.ignore_tests
            )
            review_config = create_review_config(form_inputs, diffs, project_id)
            review_config.review_id = insert_review(
                conn,
                review_config.repo_name,
                review_config.url,
                review_config.url_type,
                review_config.prompt_template_selected,
                review_config.prompt_input,
                review_config.selected_model,
                review_config.project_id,
            )
            await process_review(
                diffs=diffs,
                config=review_config,
                conn=conn,
                review_id=review_config.review_id,
            )


def get_individual_patches(diffs: DiffData) -> Tuple[List[str], List[str]]:
    """Extract individual patches and filenames from diff data."""
    return diffs.patches, diffs.file_names


def get_combined_patches(diffs: DiffData) -> Tuple[List[str], List[str]]:
    """Combine all patches into a single patch."""
    combined_patch = "\n".join(
        [f"{patch}" for fname, patch in zip(diffs.file_names, diffs.patches)]
    )
    return [combined_patch], ["Combined Files"]


async def render_patch_section(
    diffs: DiffData,
    config: ReviewConfig,
    conn: Any,
    review_id: str,
    file_name: str,
    patch: str,
    idx: int,
) -> None:
    """Render a section for a single patch including code view and analysis."""
    with st.expander(f"📁 {file_name}", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            await render_code_view(diffs, patch, file_name, config, idx)
        with col2:
            await render_analysis(diffs, config, conn, review_id, file_name, patch, idx)


async def render_analysis(
    diffs: Any,
    config: ReviewConfig,
    conn: Any,
    review_id: str,
    file_name: str,
    patch: str,
    idx: int,
) -> None:
    """Render AI analysis with better formatting and error handling."""
    sys_out = st.empty()

    try:
        # Create context object
        context = AnalysisContext(
            diffs=diffs,
            config=config,
            review_id=review_id,
            file_name=file_name,
            patch=patch,
            idx=idx,
        )

        # Configure model
        model_config = ModelConfig.from_model_name(config.selected_model)

        # Generate analysis
        response = await generate_analysis(context, model_config, sys_out)

        # Save results
        save_review(context, response, conn)

        # Render response
        key = f"ai_comment_{idx}"
        await render_response(response, key, sys_out)

    except Exception as e:
        st.error(f"Error during analysis: {str(e)}")
        raise


async def render_response(content: str, key: str, sys_out: Any) -> None:
    """Render the analysis response in the UI."""
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
        # Review header
        hcol1, hcol2 = st.columns([19, 1])  # 80/20 split
        with hcol1:
            st.markdown(f"### {review['name']}")
        with hcol2:
            if st.button("🗑️", key=f"delete-{review['id']}", use_container_width=False):
                delete_review(conn, review[0])
                st.session_state.selected_review_id = None
                st.session_state.current_view = "home"
                st.rerun()
        st.markdown('<div class="compact-divider"><hr/></div>', unsafe_allow_html=True)

        # Review header
        st.markdown(
            f"""
            **GitHub URL:** [{review['github_url']}]({review['github_url']})  
            **Template:** {review['prompt_template'] or 'Custom'}  
            **Model:** {review['llm_model'] if review['llm_model'] else 'N/A'}  
            **Prompt:** {review['prompt'] if review['prompt'] else 'None'}
        """
        )
        # Process files
        filenames = [f["file_name"] for f in files]
        patches = [f["diff"] for f in files]
        contents = [f["code"] for f in files]
        responses = [f["response"] for f in files]

    diffs = BranchDiff(review["name"], None, None, filenames, patches, contents)

    for idx, (patch, response) in enumerate(zip(patches, responses)):
        with st.expander(f"📁 {filenames[idx]}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                await render_code_view(diffs, patch, filenames[idx], None, idx)
            with col2:
                sys_out = col2.empty()
                key = f"ai_comment_{idx}"
                await render_response(response, key, sys_out)


@st.dialog("Create Project", width="large")
def dialog_create_project(conn):
    project_name = st.text_input("Project Name", st.session_state.project_name_input)
    github_repo_url = st.text_input(
        "Github Repo URL, e.g. https://github.com/karpathy/llm.c",
        st.session_state.project_github_repo_url_input,
    )
    if st.button("Submit"):
        repo_validated, validation_reason = validate_github_repo_url(github_repo_url)
        if not repo_validated:
            st.warning(validation_reason)
        else:
            project = Project(
                project_name,
                github_repo_url,
                repo_validated,
            )
            st.session_state.new_project = project
            st.rerun()


async def render_projects_page(conn):
    with st.container():
        with st.expander("Projects", expanded=True):
            if st.button(
                "📁 Create Project", type="secondary", use_container_width=False
            ):
                dialog_create_project(conn)

            new_project = st.session_state.new_project
            if new_project is not None:
                project_id = save_project(new_project, conn)
                st.session_state.new_project = None
                st.session_state.current_project_id = project_id
                st.session_state.current_view = "project-home"
                st.rerun()

    with st.container():
        with st.expander("Your Projects", expanded=True):
            projects = get_all_projects(conn)
            for project in projects:
                button_title = f"{project[1]} - {project[2]} - {project[0]}"
                if st.button(button_title, use_container_width=True):
                    st.session_state.current_project_id = project[0]
                    st.session_state.current_view = "project-home"
                    st.rerun()


async def render_project_home_page(conn, project_id):
    with st.container():
        with st.expander(f"Project - {project_id}", expanded=True):
            st.write("Indexed Status")
            if st.button("Add Review", type="primary", use_container_width=False):
                st.session_state.selected_review_id = None
                st.session_state.current_project_id = project_id
                st.session_state.current_view = "home"
                st.rerun()
            if st.button(
                "Add Embeddings Index", type="secondary", use_container_width=False
            ):
                st.rerun()

    project_reviews = get_all_project_reviews(conn, project_id)
    with st.container():
        with st.expander(f"Recent Reviews", expanded=True):
            for review in project_reviews:
                button_title = f"{review[2]} - {review[1]} - {review[0]}"
                if st.button(button_title, use_container_width=True):
                    st.session_state.selected_review_id = review[0]
                    st.session_state.current_view = "review"
                    st.rerun()
