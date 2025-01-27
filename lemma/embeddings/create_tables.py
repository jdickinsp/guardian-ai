import sqlite3

from lemma.db import create_connection


def create_embeddings_tables(conn: sqlite3.Connection):
    """
    Extend existing DB schema to store code chunks and embeddings.
    We'll create two tables:
    1) file_chunks: store chunk text, associated repo, file path, etc.
    2) file_chunk_embeddings: store the vector dimension, vector data (BLOB).
    """
    try:
        c = conn.cursor()

        # Table to store textual info for each chunk
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS file_chunks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                repo_path TEXT NOT NULL, 
                file_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Optionally store the embeddings in a separate table
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS file_chunk_embeddings (
                chunk_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                embedding_dim INTEGER NOT NULL,
                PRIMARY KEY (chunk_id),
                FOREIGN KEY (chunk_id) REFERENCES file_chunks (id)
            );
        """
        )

        # Add an index on project_id + file_path for quick lookups
        c.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_chunks_project_id 
            ON file_chunks (project_id);
        """
        )

        c.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_chunks_path 
            ON file_chunks (file_path);
        """
        )

        conn.commit()

    except Exception as e:
        print(f"Error creating embeddings tables: {e}")


if __name__ == "__main__":
    conn = create_connection("bin/code_reviews.db")
    create_embeddings_tables(conn)
