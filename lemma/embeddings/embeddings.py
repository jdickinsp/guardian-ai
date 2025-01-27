import os
import uuid
from typing import List, Dict, Any
import faiss
import sqlite3
import ollama


EMBEDDING_DIM = 768


def create_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates embeddings for a list of texts using the Ollama 'nomic-embed-text' model.

    Args:
        texts (List[str]): A list of strings to embed.

    Returns:
        List[List[float]]: A list of embeddings, each being a list of floats.
    """
    if not texts:
        return []

    try:
        embeddings = []
        texts_count = len(texts)
        progress = max(texts_count / 20, 1)
        for i, text in enumerate(texts):
            if not text.strip():
                # Skip empty or whitespace-only texts
                print("Skipping empty text.")
                embeddings.append([0.0] * EMBEDDING_DIM)
                continue
            response = ollama.embed(model="nomic-embed-text", input=text)
            embedding = response["embeddings"][0]
            if i % progress == 0:
                print("progess: ", ((i + 1) / texts_count) * 100)
            if not embedding:
                # If embedding fails or returns empty, append a zero vector
                print(f"Failed to generate embedding for text: '{text}'")
                embeddings.append([0.0] * EMBEDDING_DIM)
                continue
            embeddings.append(embedding)
        return embeddings
    except Exception as e:
        print(f"Error generating embeddings with Ollama: {e}")
        return []


def create_vector_indexes(
    conn: sqlite3.Connection,
    project_id: str,
    repo_local_path: str,
    all_chunks: List[Dict[str, Any]],
) -> str:
    """
    Creates embeddings for each chunk, builds a FAISS index,
    writes the index to a local file, and stores chunk metadata in `file_chunks` table.

    Returns the path to the FAISS index file.
    """
    # Ensure we have the embeddings tables:
    create_embeddings_tables(conn)

    # Build texts from all_chunks:
    texts = [chunk["chunk_text"] for chunk in all_chunks]
    embeddings = create_embeddings(texts)

    # Build the FAISS index
    if len(embeddings) == 0:
        raise ValueError("No embeddings generated, cannot build FAISS index.")

    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)  # simple L2 index
    faiss_vectors = []

    # Insert chunk metadata and embeddings into DB
    c = conn.cursor()

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
        # convert float list to binary blob
        # faiss requires float32
        import numpy as np

        arr = np.array(vector, dtype="float32")
        bin_data = arr.tobytes()

        c.execute(
            """
            INSERT INTO file_chunk_embeddings(chunk_id, embedding, embedding_dim)
            VALUES(?,?,?)
        """,
            (chunk_id, bin_data, dim),
        )

        # We'll store the vector for the FAISS index in memory so we can add them all at once
        faiss_vectors.append(arr)

    conn.commit()

    # Now build the FAISS index from the vectors
    vectors_np = np.vstack(faiss_vectors)
    index.add(vectors_np)

    # Save index to file
    index_file = os.path.join("bin", f"{project_id}_index.faiss")
    os.makedirs("bin", exist_ok=True)
    faiss.write_index(index, index_file)

    print(f"FAISS index saved to {index_file}")
    return index_file


if __name__ == "__main__":
    from lemma.db import create_connection, db_init
    from lemma.embeddings.manage_repo import clone_github_repo
    from lemma.embeddings.create_tables import create_embeddings_tables
    from lemma.embeddings.segment import segment_codebase

    # 0) Connect to DB & ensure migrations
    conn = create_connection("bin/code_reviews_copy.db")
    db_init(conn)

    # 1) Clone a repo
    test_repo_url = "https://github.com/karpathy/llm.c"
    local_repo_dir = clone_github_repo(test_repo_url)

    # 2) Segment code
    all_chunks = segment_codebase(local_repo_dir, max_chunk_size=100, ignore_tests=True)

    # Suppose we have a known 'project_id' in the DB:
    project_id = "cb655754-dbc2-4781-a7ef-4ddbc423bc1b"

    # 3 & 4) Create embeddings & build FAISS index
    index_path = create_vector_indexes(conn, project_id, local_repo_dir, all_chunks)

    # # Clean up cloned repo if desired
    # shutil.rmtree(local_repo_dir, ignore_errors=True)

    conn.close()
