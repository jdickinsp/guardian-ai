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
    1) Embed the query_text using the same method as create_embeddings
    2) Load the FAISS index from disk
    3) Perform a similarity search
    4) Lookup chunk metadata from DB
    5) Return the top_k results
    """
    index_file = os.path.join("bin", f"{project_id}_index.faiss")
    if not os.path.exists(index_file):
        raise FileNotFoundError(f"FAISS index file not found: {index_file}")

    # Embed the new context
    embed_vecs = create_embeddings([query_text])  # returns a List[List[float]]
    if not embed_vecs:
        return []
    query_vec = embed_vecs[0]

    query_arr = np.array(query_vec, dtype="float32").reshape(1, -1)
    print(f"Query vector (first 10 elements): {query_arr[0][:10]}")
    print(f"Query vector norm: {np.linalg.norm(query_arr)}")

    # Reload the FAISS index
    index = faiss.read_index(index_file)
    inspect_faiss_index(index)
    print("Index total vectors:", index.ntotal)
    print("Index dimension:", index.d)
    print("Query vector dimension:", len(query_vec))

    query_arr = np.array(query_vec, dtype="float32").reshape(1, -1)

    # Search
    D, I = index.search(query_arr, top_k)

    # After FAISS search
    print("Distances (D):", D)
    print("Indices (I):", I)
    print("First row of distances:", D[0])
    print("First row of indices:", I[0])

    # The indexes I are the row positions in the original add(...) call,
    # which we must cross-reference with the chunk table entries we inserted.
    # Because we inserted them in a known order, let's store row -> chunk_id somewhere,
    # OR simply rely on the fact we inserted them in a specific sequence.

    # In this example, we do not store a direct row->chunk_id map in memory,
    # but we can retrieve them from the 'file_chunk_embeddings' table
    # in insertion order. We do that by using an auto-increment rowid or by
    # joining in the order they were inserted.

    # For simplicity, let's add an auto-increment rowid to file_chunk_embeddings
    # or store them in a map. Another approach: we store them in memory while building
    # index. But for demonstration, let's do a quick approach:
    #  - We add an integer sequence as we do c.execute, the i is in memory.
    #  - We'll store them in an ephemeral 'embedding_order' array.
    #
    # A more robust approach is to store chunk_id in memory in the same order as
    # we add vectors to the FAISS index. Then we can do chunk_id_map[I[j]].

    # For demonstration, let's fetch them from DB in insertion order:
    # This is naive, but we’ll show how it can be done. We'll assume the insertion
    # order is stable and rowid increments in order.

    # If you prefer, store a separate list [chunk_id_0, chunk_id_1, ...] in memory
    # during index creation. For this snippet, let's do a small hack.

    c = conn.cursor()
    c.execute(
        """
        SELECT rowid, chunk_id 
        FROM file_chunk_embeddings
        WHERE chunk_id IN (SELECT id FROM file_chunks WHERE project_id=?)
        ORDER BY rowid ASC
    """,
        (project_id,),
    )
    row_map = c.fetchall()  # e.g. [(1, 'uuid1'), (2, 'uuid2'), ...]

    # row_map[i-1][1] => chunk_id
    # We'll build a simple list of chunk_id in the insertion order
    chunk_id_in_order = [row[1] for row in row_map]

    print(f"Total chunk IDs in order: {len(chunk_id_in_order)}")  # Should be 320
    print("First 10 chunk IDs:", chunk_id_in_order[:10])
    print("Last 10 chunk IDs:", chunk_id_in_order[-10:])

    # Now for the top_k indices
    results = []
    for dist, idx_val in zip(D[0], I[0]):
        print(f"FAISS returned index: {idx_val} with distance: {dist}")
        if idx_val < len(chunk_id_in_order):
            chunk_id = chunk_id_in_order[idx_val]
            print(f"Mapped chunk_id: {chunk_id}")
            # Retrieve the chunk row from DB
            c.execute(
                """
                SELECT repo_path, file_path, chunk_index, chunk_text
                FROM file_chunks
                WHERE id=?
            """,
                (chunk_id,),
            )
            chunk_row = c.fetchone()
            if not chunk_row:
                print(f"Chunk ID {chunk_id} does not exist in file_chunks!")
            if chunk_row:
                repo_path, file_path, chunk_index, chunk_text = chunk_row
                print(
                    f"Retrieved chunk: {chunk_id}, Path: {file_path}, Index: {chunk_index}"
                )
                results.append(
                    {
                        "chunk_id": chunk_id,
                        "repo_path": repo_path,
                        "file_path": file_path,
                        "chunk_index": chunk_index,
                        "chunk_text": chunk_text,
                        "distance": dist,
                    }
                )
        else:
            print(f"Index {idx_val} is out of bounds for chunk_id_in_order")

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
    project_id = "cb655754-dbc2-4781-a7ef-4ddbc423bc1b"
    top_results = search_similar_code(conn, project_id, query_text, top_k=3)

    print("Top results:")
    for r in top_results:
        print(r["file_path"], "chunk:", r["chunk_index"], "dist:", r["distance"])
