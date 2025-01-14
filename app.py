import asyncio
import streamlit as st
from views.ui import render_create_review_page, render_sidebar, render_view_review_page
from db import create_connection, db_init, get_all_reviews

# Set page configuration
st.set_page_config(
    page_title="Code Review AI",
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

async def main():
    init_session_state()
    
    conn = create_connection("bin/code_reviews.db")
    if conn is None:
        st.error("Database connection failed!")
        return

    if not st.session_state.has_run:
        db_init(conn)
        st.session_state.has_run = True

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
