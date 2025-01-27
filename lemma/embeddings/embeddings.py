from typing import List

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
        print(f"embedding: {len(texts)} chunks")
        for text in texts:
            if not text.strip():
                # Skip empty or whitespace-only texts
                print("Skipping empty text.")
                embeddings.append([0.0] * EMBEDDING_DIM)
                continue
            response = ollama.embed(model="nomic-embed-text", input=text)
            embedding = response["embeddings"][0]
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


if __name__ == "__main__":
    from lemma.db import create_connection, db_init
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

    # Generate embeddings
    texts = [chunk["chunk_text"] for chunk in all_chunks]
    embeddings = create_embeddings(texts)
    print(embeddings[0])

    conn.close()
