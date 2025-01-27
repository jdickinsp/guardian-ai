import os
import sqlite3
from typing import Any, Dict, List

import faiss
import numpy as np

from lemma.embeddings.embeddings import create_embeddings


def search_similar_code(
    conn: sqlite3.Connection, project_id: str, query_text: str, top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Performs a similarity search using FAISS and retrieves corresponding code chunks.

    Args:
        conn (sqlite3.Connection): SQLite connection to the database.
        project_id (str): The project ID to search within.
        query_text (str): The text query to embed and search.
        top_k (int): Number of closest matches to retrieve.

    Returns:
        List[Dict[str, Any]]: A list of similar code chunks with metadata and distances.
    """
    index_file = os.path.join("bin", f"{project_id}_index.faiss")
    if not os.path.exists(index_file):
        raise FileNotFoundError(f"FAISS index file not found: {index_file}")

    # Embed the query text
    embed_vecs = create_embeddings([query_text])  # returns a List[List[float]]
    if not embed_vecs:
        print("No embeddings returned for the query.")
        return []
    query_vec = embed_vecs[0]

    # Convert to float32 NumPy array
    query_arr = np.array(query_vec, dtype="float32").reshape(1, -1)

    # Reload the FAISS index
    index = faiss.read_index(index_file)

    # Search FAISS index
    D, I = index.search(query_arr, top_k)
    print(f"FAISS search returned distances: {D}")
    print(f"FAISS search returned indices: {I}")

    # Load FAISS index mapping
    c = conn.cursor()
    # Ensure faiss_indices is a list of integers
    faiss_indices = [int(i) for i in I[0].tolist()]

    if not faiss_indices:
        print("No FAISS indices returned from search.")
        return []
    # Prepare placeholders for SQL IN clause
    placeholders = ",".join(["?"] * len(faiss_indices))
    c.execute(
        f"""
        SELECT faiss_index, chunk_id FROM faiss_index_mapping
        WHERE project_id = ? AND faiss_index IN ({placeholders})
    """,
        (project_id, *faiss_indices),
    )
    mapping_rows = c.fetchall()
    print(f"Mapping rows retrieved: {mapping_rows}")

    # Create a dictionary {faiss_index: chunk_id}
    faiss_to_chunk = {row[0]: row[1] for row in mapping_rows}

    if not faiss_to_chunk:
        print("No valid chunk IDs found for the given FAISS indices.")
        return []

    # Fetch chunk details based on chunk_ids
    chunk_ids = list(faiss_to_chunk.values())
    placeholders = ",".join(["?"] * len(chunk_ids))
    c.execute(
        f"""
        SELECT id, repo_path, file_path, chunk_index, chunk_text
        FROM file_chunks
        WHERE id IN ({placeholders})
        """,
        chunk_ids,
    )
    chunks = {
        row[0]: {
            "repo_path": row[1],
            "file_path": row[2],
            "chunk_index": row[3],
            "chunk_text": row[4],
        }
        for row in c.fetchall()
    }

    # Build the results list
    results = []
    for dist, faiss_idx in zip(D[0], I[0]):
        chunk_id = faiss_to_chunk.get(faiss_idx)
        if not chunk_id:
            print(f"No chunk_id found for FAISS index {faiss_idx}")
            continue
        chunk_data = chunks.get(chunk_id)
        if not chunk_data:
            print(f"No chunk data found for chunk_id {chunk_id}")
            continue
        results.append(
            {
                "chunk_id": chunk_id,
                "repo_path": chunk_data["repo_path"],
                "file_path": chunk_data["file_path"],
                "chunk_index": chunk_data["chunk_index"],
                "chunk_text": chunk_data["chunk_text"],
                "distance": dist,
            }
        )

    if not results:
        print("No valid chunk data found for the given FAISS indices.")
    else:
        print(f"Found {len(results)} similar code chunks.")

    return results


def inspect_faiss_index(index: faiss.Index, num_vectors: int = 5):
    print(f"Total vectors in index: {index.ntotal}")
    for i in range(min(num_vectors, index.ntotal)):
        vec = np.zeros(index.d, dtype="float32")
        index.reconstruct(i, vec)
        print(f"Vector {i}:")
        print(f"  First 10 elements: {vec[:10]}")
        print(f"  Norm: {np.linalg.norm(vec)}")
        print()


if __name__ == "__main__":
    from lemma.db import create_connection, db_init

    conn = create_connection("bin/code_reviews_copy.db")
    db_init(conn)  # creates base tables if missing

    # 5) Searching
    query_text = "Optimize a function in c for the gpu"
    project_id = "581d39d0-ab13-444d-a8de-053f0ba6eae2"
    top_results = search_similar_code(conn, project_id, query_text, top_k=3)

    print("Top results:")
    for r in top_results:
        print(r["file_path"], "chunk:", r["chunk_index"], "dist:", r["distance"])
