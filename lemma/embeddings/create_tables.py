import sqlite3

from lemma.db import create_connection


def create_embeddings_tables(conn: sqlite3.Connection):
    """
    Extend existing DB schema to store code chunks and embeddings.
       We'll create three tables:
       1) file_chunks: store chunk text, associated repo, file path, etc.
       2) file_chunk_embeddings: store the vector dimension, vector data (BLOB).
       3) faiss_index_mapping: map FAISS index integers to chunk_ids.
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

        # Table to store embeddings for each chunk
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

        # Table to map FAISS indices to chunk_ids
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS faiss_index_mapping (
                project_id TEXT NOT NULL,
                faiss_index INTEGER NOT NULL,
                chunk_id TEXT NOT NULL,
                PRIMARY KEY (project_id, faiss_index),
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


def delete_all_embeddings(conn):
    """
    Delete all records from file_chunks and file_chunk_embeddings tables.
    """
    try:
        c = conn.cursor()
        c.execute("DELETE FROM faiss_index_mapping;")
        c.execute("DELETE FROM file_chunk_embeddings;")
        c.execute("DELETE FROM file_chunks;")
        conn.commit()
        print("All embeddings and file chunks deleted successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error deleting embeddings data: {e}")

    c = conn.cursor()
    # Free up space
    c.execute("VACUUM;")
    conn.commit()


if __name__ == "__main__":
    # conn = create_connection("bin/code_reviews_copy.db")
    # create_embeddings_tables(conn)
    # delete_all_embeddings(conn)
    pass
