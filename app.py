import asyncio
import streamlit as st
from views.ui import (
    render_create_review_page,
    render_project_home_page,
    render_sidebar,
    render_view_review_page,
    render_projects_page,
)
from db import create_connection, db_init

# Set page configuration
st.set_page_config(
    page_title="Lemma",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better UI
with open("./views/style.css") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True,
    )


def init_session_state():
    if "url_input" not in st.session_state:
        st.session_state.url_input = ""
    if "selected_review_id" not in st.session_state:
        st.session_state.selected_review_id = None
    if "reviews" not in st.session_state:
        st.session_state.reviews = []
    if "has_run" not in st.session_state:
        st.session_state.has_run = False
    if "current_view" not in st.session_state:
        st.session_state.current_view = "home"
    if "project_name_input" not in st.session_state:
        st.session_state.project_name_input = ""
    if "project_github_repo_url_input" not in st.session_state:
        st.session_state.project_github_repo_url_input = ""
    if "current_project_id" not in st.session_state:
        st.session_state.current_project_id = None
    if "new_project" not in st.session_state:
        st.session_state.new_project = None


async def main():
    init_session_state()

    conn = create_connection("bin/code_reviews.db")
    if conn is None:
        st.error("Database connection failed!")
        return

    if not st.session_state.has_run:
        db_init(conn)
        st.session_state.has_run = True

    await render_sidebar(conn)

    if st.session_state.selected_review_id:
        await render_view_review_page(
            conn,
        )

    if st.session_state.current_view == "home":
        await render_create_review_page(conn, st.session_state.current_project_id)
    elif st.session_state.current_view == "project-home":
        await render_project_home_page(conn, st.session_state.current_project_id)
    elif st.session_state.current_view == "projects":
        await render_projects_page(conn)

    if conn:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
