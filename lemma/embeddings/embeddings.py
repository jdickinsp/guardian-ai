import os
import uuid
import shutil
import faiss
import sqlite3

from pathlib import Path
from typing import List, Dict, Any

# If you want to call the Python API for Nomic:
# from nomic import embedding as nomic_embedding
# from nomic import Atlas

from lemma.db import create_connection, db_init
from lemma.detect import is_ignored_file
from lemma.embeddings.manage_repo import clone_github_repo
from lemma.embeddings.create_tables import create_embeddings_tables


def segment_codebase(
    repo_local_path: str, max_chunk_size: int = 200, ignore_tests: bool = True
) -> List[Dict[str, Any]]:
    """
    Recursively walk the local repo directory, skipping ignored files,
    and segment each file's content into chunks of up to `max_chunk_size` lines.

    Returns a list of dicts:
    [
      {
         'file_path': 'relative/path/to/file.py',
         'chunk_index': 0,
         'chunk_text': '...some lines of code...',
      },
      ...
    ]
    """
    all_chunks = []
    repo_path = Path(repo_local_path).resolve()
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden folders like .git
        if root.endswith(".git"):
            continue

        for filename in files:
            full_path = Path(root) / filename
            rel_path = full_path.relative_to(repo_path).as_posix()

            # Check if we should skip this file
            if is_ignored_file(filename):
                continue
            if ignore_tests and "test" in filename.lower():
                # Very naive skipping logic.
                # In lemma.detect.is_test_file, there's a more robust check if needed.
                continue

            # Read the file
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"Skipping file {rel_path}, error reading: {e}")
                continue

            # Break into line-based chunks
            chunk_start = 0
            chunk_index = 0
            while chunk_start < len(lines):
                chunk_end = chunk_start + max_chunk_size
                chunk_lines = lines[chunk_start:chunk_end]
                chunk_text = "".join(chunk_lines)

                all_chunks.append(
                    {
                        "file_path": rel_path,
                        "chunk_index": chunk_index,
                        "chunk_text": chunk_text,
                    }
                )

                chunk_index += 1
                chunk_start = chunk_end

    return all_chunks


def create_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings for a list of strings using Nomic.
    Example uses the `nomic` python library.
    Alternatively, to call the CLI `nomic-embed-text`, you might do:

        result = subprocess.run(
            ["nomic-embed-text", "--some-args"],
            input="\n".join(texts),
            text=True,
            capture_output=True
        )
        embeddings = parse_that_output(result.stdout)

    For demonstration, we'll show a mock usage using `nomic` library
    if you have `pip install nomic`. If not, replace with your actual pipeline.
    """
    try:
        # Example with Python's "nomic" library:
        # embeddings = nomic_embedding.embed_text(texts)
        # return embeddings

        # Stub, random or zero vectors. Replace with real calls as needed.
        dim = 384  # Just a guess for demonstration
        embeddings = []
        for text in texts:
            # Fake embedding:  all zeros
            embeddings.append([0.0] * dim)
        return embeddings

    except Exception as e:
        print(f"Error generating embeddings with Nomic: {e}")
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


def search_similar_code(
    conn: sqlite3.Connection, project_id: str, new_context: str, top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    1) Embed the new_context using the same method as create_embeddings
    2) Load the FAISS index from disk
    3) Perform a similarity search
    4) Lookup chunk metadata from DB
    5) Return the top_k results
    """
    index_file = os.path.join("bin", f"{project_id}_index.faiss")
    if not os.path.exists(index_file):
        raise FileNotFoundError(f"FAISS index file not found: {index_file}")

    # Embed the new context
    embed_vecs = create_embeddings([new_context])  # returns a List[List[float]]
    if not embed_vecs:
        return []
    query_vec = embed_vecs[0]

    # Reload the FAISS index
    index = faiss.read_index(index_file)

    # Convert to float32 NumPy
    import numpy as np

    query_arr = np.array(query_vec, dtype="float32").reshape(1, -1)

    # Search
    D, I = index.search(query_arr, top_k)

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

    # Now for the top_k indices
    results = []
    for dist, idx_val in zip(D[0], I[0]):
        if idx_val < len(chunk_id_in_order):
            chunk_id = chunk_id_in_order[idx_val]
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
            if chunk_row:
                repo_path, file_path, chunk_index, chunk_text = chunk_row
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

    return results


if __name__ == "__main__":

    # 0) Connect to DB & ensure migrations
    conn = create_connection("bin/code_reviews.db")
    db_init(conn)  # creates base tables if missing
    create_embeddings_tables(conn)  # ensures chunk-related tables exist

    # 1) Clone a repo
    # e.g. "https://github.com/username/some_project.git"
    test_repo_url = "https://github.com/karpathy/llm.c"
    local_repo_dir = clone_github_repo(test_repo_url)

    # 2) Segment code
    all_chunks = segment_codebase(local_repo_dir, max_chunk_size=100, ignore_tests=True)

    # Suppose we have a known 'project_id' in the DB:
    # (If you don't have one, insert into projects & get the returned ID.)
    # For demo, let's pretend we have one:
    project_id = "cb655754-dbc2-4781-a7ef-4ddbc423bc1b"

    # 3 & 4) Create embeddings & build FAISS index
    index_path = create_vector_indexes(conn, project_id, local_repo_dir, all_chunks)

    # 5) Searching
    query_text = "Optimize a function in c for the gpu"
    top_results = search_similar_code(conn, project_id, query_text, top_k=3)

    print("Top results:")
    for r in top_results:
        print(r["file_path"], "chunk:", r["chunk_index"], "dist:", r["distance"])

    # Clean up cloned repo if desired
    shutil.rmtree(local_repo_dir, ignore_errors=True)

    conn.close()
