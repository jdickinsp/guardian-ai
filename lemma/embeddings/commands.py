import sqlite3

from lemma.db import get_project
from lemma.embeddings.manage_repo import clone_github_repo


def create_embeddings_index(conn: sqlite3.Connection, project_id: str):
    """
    look up project_id => github_repo_url
    download repo
    save hash in project.latest_commit

    segment codebase

    create embeddings

    save index and database

    TODO: add option to use embeddings
    """
    project = get_project(conn, project_id)
    print("project", project)
    # local_repo_dir = clone_github_repo(project[2])
