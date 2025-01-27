import os
import sqlite3
import uuid
from typing import Any, Dict, List

import faiss
import numpy as np

from lemma.embeddings.create_tables import create_embeddings_tables
from lemma.embeddings.embeddings import create_embeddings


def create_vector_indexes(
    conn: sqlite3.Connection,
    project_id: str,
    repo_local_path: str,
    all_chunks: List[Dict[str, Any]],
) -> str:
    """
    Generates vector embeddings for code chunks, creates a FAISS index, and stores relevant
    data in the SQLite database for future searches.

    Steps:
    1. Ensure necessary database tables are created.
    2. Clear existing FAISS index mappings for the given project.
    3. Generate embeddings for the provided code chunks.
    4. Save chunk metadata and embeddings to the database.
    5. Build and save a FAISS index file to disk.
    6. Populate the index-to-chunk mapping table.

    Args:
        conn (sqlite3.Connection): SQLite database connection.
        project_id (str): Unique identifier of the project.
        repo_local_path (str): Local path to the cloned GitHub repository.
        all_chunks (List[Dict[str, Any]]): List of code chunks with file metadata.

    Returns:
        str: The file path of the saved FAISS index.

    Raises:
        ValueError: If embeddings fail to generate or no valid embeddings exist to build an index.

    Example Usage:
        >>> conn = sqlite3.connect('bin/code_reviews_copy.db')
        >>> project_id = 'cb655754-dbc2-4781-a7ef-4ddbc423bc1b'
        >>> repo_local_path = '/local/path/to/repo'
        >>> all_chunks = [
        ...     {'file_path': 'file1.py', 'chunk_index': 0, 'chunk_text': 'def foo(): pass'}
        ... ]
        >>> index_file = create_vector_indexes(conn, project_id, repo_local_path, all_chunks)
        >>> print(f"FAISS index created at: {index_file}")
    """
    # Ensure tables are created
    create_embeddings_tables(conn)

    c = conn.cursor()

    # **Clear existing faiss_index_mapping entries for this project**
    c.execute("DELETE FROM faiss_index_mapping WHERE project_id = ?;", (project_id,))
    conn.commit()
    print(f"Cleared existing faiss_index_mapping entries for project {project_id}.")

    # Generate embeddings
    texts = [chunk["chunk_text"] for chunk in all_chunks]
    embeddings = create_embeddings(texts)

    if not embeddings:
        raise ValueError("No embeddings generated, cannot build FAISS index.")

    dim = len(embeddings[0])
    print(f"FAISS index expected dimension: {dim}")

    index = faiss.IndexFlatL2(dim)
    faiss_vectors = []
    faiss_index_map = []

    for i, chunk_data in enumerate(all_chunks):
        chunk_text = chunk_data["chunk_text"]
        file_path = chunk_data["file_path"]
        chunk_idx = chunk_data["chunk_index"]
        vector = embeddings[i]

        # Insert into file_chunks
        chunk_id = str(uuid.uuid4())
        c.execute(
            """
            INSERT INTO file_chunks(id, project_id, repo_path, file_path, chunk_index, chunk_text)
            VALUES(?,?,?,?,?,?)
        """,
            (chunk_id, project_id, repo_local_path, file_path, chunk_idx, chunk_text),
        )

        # Insert into file_chunk_embeddings
        arr = np.array(vector, dtype="float32")

        if arr.shape[0] != dim:
            print(
                f"Warning: Mismatched embedding dimension for chunk {chunk_id}, skipping."
            )
            continue

        bin_data = arr.tobytes()
        c.execute(
            """
            INSERT INTO file_chunk_embeddings(chunk_id, embedding, embedding_dim)
            VALUES(?,?,?)
        """,
            (chunk_id, bin_data, dim),
        )

        # Skip zero embeddings
        if np.linalg.norm(arr) == 0:
            print(f"Skipping zero embedding for chunk: {file_path} - index {chunk_idx}")
            continue

        faiss_vectors.append(arr)
        faiss_index_map.append(chunk_id)

    conn.commit()

    # Build FAISS index
    if not faiss_vectors:
        raise ValueError("No valid embeddings to add to FAISS index.")

    vectors_np = np.vstack(faiss_vectors)
    print(f"Shape of vectors_np being added to FAISS: {vectors_np.shape}")
    assert (
        vectors_np.shape[1] == dim
    ), f"Embedding dimension mismatch: Expected {dim}, got {vectors_np.shape[1]}"

    index.add(vectors_np)

    # save index to file
    index_file = os.path.join("bin", f"{project_id}_index.faiss")
    os.makedirs("bin", exist_ok=True)
    faiss.write_index(index, index_file)

    print(f"FAISS index saved to {index_file}")

    # Populate faiss_index_mapping
    for faiss_idx, chunk_id in enumerate(faiss_index_map):
        c.execute(
            """
            INSERT INTO faiss_index_mapping(project_id, faiss_index, chunk_id)
            VALUES(?,?,?)
        """,
            (project_id, faiss_idx, chunk_id),
        )

    conn.commit()
    print(f"FAISS index mapping table populated with {len(faiss_index_map)} entries.")

    return index_file


if __name__ == "__main__":
    from lemma.db import create_connection, db_init
    from lemma.embeddings.create_vector_indexes import create_vector_indexes
    from lemma.embeddings.manage_repo import clone_github_repo
    from lemma.embeddings.segment import segment_codebase

    # 0) Connect to DB & ensure migrations
    conn = create_connection("bin/code_reviews_copy.db")
    db_init(conn)

    # 1) Clone a repo
    test_repo_url = "https://github.com/karpathy/nanoGPT"
    local_repo_dir = clone_github_repo(test_repo_url)

    # 2) Segment code
    all_chunks = segment_codebase(local_repo_dir, max_chunk_size=100, ignore_tests=True)

    # Suppose we have a known 'project_id' in the DB:
    project_id = "581d39d0-ab13-444d-a8de-053f0ba6eae2"

    # 3 & 4) Create embeddings & build FAISS index
    index_path = create_vector_indexes(conn, project_id, local_repo_dir, all_chunks)

    # # Clean up cloned repo if desired
    # shutil.rmtree(local_repo_dir, ignore_errors=True)

    conn.close()
