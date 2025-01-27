import shutil
import sqlite3

from lemma.db import get_project
from lemma.embeddings.create_vector_indexes import create_vector_indexes
from lemma.embeddings.manage_repo import (
    clone_github_repo,
    get_latest_commit_from_github,
    parse_repo_info_from_github,
)
from lemma.embeddings.segment import segment_codebase


def create_embeddings_index(conn: sqlite3.Connection, project_id: str):
    """
    Creates an embeddings index for a given project by performing the following steps:

    1. Retrieve the project details from the database using the provided `project_id`.
    2. Clone the project's GitHub repository to a local directory.
    3. Retrieve and store the latest commit hash in the database.
    4. Segment the codebase into manageable chunks for processing.
    5. Generate embeddings for the segmented code chunks.
    6. Create a FAISS index and store chunk data in the database.
    7. Clean up the cloned repository to free disk space.

    Args:
        conn (sqlite3.Connection): An active SQLite database connection.
        project_id (str): The unique identifier of the project.

    Returns:
        str: The file path of the saved FAISS index.

    Raises:
        ValueError: If the project is not found, segmentation fails, or embedding generation fails.
        Exception: If any unexpected error occurs during the process.

    Example Usage:
        >>> conn = sqlite3.connect('bin/code_reviews_copy.db')
        >>> project_id = 'cb655754-dbc2-4781-a7ef-4ddbc423bc1b'
        >>> index_file = create_embeddings_index(conn, project_id)
        >>> print(f"Embeddings index saved at: {index_file}")
    """
    if project_id is None:
        print("Error: project_id is None")
        return None

    # 1. Look up the project in the database
    project = get_project(conn, project_id)
    if not project:
        raise ValueError(f"Project with ID {project_id} not found.")

    repo_url = project["github_repo_url"]
    print(f"Attempt to clone repository: {repo_url}")

    # 2. Clone GitHub repository
    local_repo_path = clone_github_repo(repo_url)

    # 3. Get the latest commit hash
    owner, repo, _ = parse_repo_info_from_github(repo_url)
    latest_commit = get_latest_commit_from_github(owner, repo)
    print(f"Latest commit hash: {latest_commit}")

    # Save the latest commit hash in the database
    c = conn.cursor()
    c.execute(
        "UPDATE projects SET latest_commit = ? WHERE id = ?",
        (latest_commit, project_id),
    )
    conn.commit()
    print("Latest commit hash saved in database.")

    # 4. Segment the codebase into chunks
    print("Segmenting codebase...")
    all_chunks = segment_codebase(
        local_repo_path, max_chunk_size=200, ignore_tests=True
    )

    if not all_chunks:
        raise ValueError("No code chunks were generated from segmentation.")

    print(f"Segmented {len(all_chunks)} chunks from the codebase.")

    # 5. Generate embeddings and save index/database
    index_path = create_vector_indexes(conn, project_id, local_repo_path, all_chunks)
    print(f"FAISS index saved at: {index_path}")

    # Clean up cloned repository after processing
    shutil.rmtree(local_repo_path, ignore_errors=True)
    print("Temporary repository deleted.")

    print("Embedding index creation completed successfully.")
    return index_path
