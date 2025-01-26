import sqlite3
from sqlite3 import Error
import uuid


def create_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"SQLite Database created and connected to {db_file}")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Error as e:
        print(f"Error: {e}")
    return conn


def create_tables(conn):
    """Create tables in the SQLite database"""
    try:
        sql_create_reviews_table = """
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            github_url TEXT NOT NULL,
            github_url_type VARCHAR(100) NULL,
            prompt_template TEXT NULL,
            prompt TEXT NULL,
            llm_model VARCHAR(100) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );"""

        sql_create_files_table = """
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            review_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            diff TEXT,
            code TEXT,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (review_id) REFERENCES reviews (id)
        );"""

        c = conn.cursor()
        c.execute(sql_create_reviews_table)
        c.execute(sql_create_files_table)

        # Create a trigger to automatically update the updated_at field
        c.execute(
            """
        CREATE TRIGGER IF NOT EXISTS update_timestamp
        AFTER UPDATE ON reviews
        FOR EACH ROW
        BEGIN
            UPDATE reviews SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        """
        )
        # Create an index on the created_at column
        c.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_created_at ON reviews (created_at)
        """
        )
        # Create a trigger to automatically update the updated_at field
        c.execute(
            """
        CREATE TRIGGER IF NOT EXISTS update_timestamp
        AFTER UPDATE ON files
        FOR EACH ROW
        BEGIN
            UPDATE files SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        """
        )
        print("Tables 'reviews' and 'files' created successfully")
    except Error as e:
        raise Error(f"Database error: {e}")


def insert_review(
    conn, name, github_url, github_url_type, prompt_template, prompt, llm_model
):
    """Insert a new review into the reviews table"""
    try:
        if name is None:
            raise ValueError("Name cannot be None")
        review_id = str(uuid.uuid4())
        sql_insert_review = """INSERT INTO reviews(id, name, github_url, github_url_type, prompt_template, prompt, llm_model)
                              VALUES(?,?,?,?,?,?,?)"""
        cur = conn.cursor()
        cur.execute(
            sql_insert_review,
            (
                review_id,
                name,
                github_url,
                github_url_type,
                prompt_template,
                prompt,
                llm_model,
            ),
        )
        conn.commit()
        return review_id
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Database error: {e}")
    except ValueError as e:
        raise sqlite3.Error(f"Database error: {e}")


def insert_file(conn, review_id, file_name, diff, code, response):
    """Insert a new file into the files table"""
    try:
        c = conn.cursor()
        # First, check if the review exists
        c.execute("SELECT id FROM reviews WHERE id=?", (review_id,))
        if c.fetchone() is None:
            raise ValueError(f"Review with id {review_id} does not exist")

        file_id = str(uuid.uuid4())
        c.execute(
            """INSERT INTO files (id, review_id, file_name, diff, code, response)
                     VALUES (?, ?, ?, ?, ?, ?)""",
            (file_id, review_id, file_name, diff, code, response),
        )
        conn.commit()
        return file_id
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Database error: {e}")


def delete_review(conn, review_id):
    """Delete a review and its associated files from the database"""
    try:
        sql_delete_files = """DELETE FROM files WHERE review_id = ?"""
        sql_delete_review = """DELETE FROM reviews WHERE id = ?"""
        cur = conn.cursor()
        cur.execute(sql_delete_files, (review_id,))
        cur.execute(sql_delete_review, (review_id,))
        conn.commit()
    except Error as e:
        raise Error(f"Database error: {e}")


def get_all_reviews(conn):
    """
    Query all rows in the reviews table
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reviews order by reviews.created_at DESC")
        rows = cur.fetchall()
        return rows
    except Error as e:
        raise Error(f"Database error: {e}")


def get_review_with_files(conn, review_id):
    """
    Query a review and all its associated files
    """
    try:
        cur = conn.cursor()
        # Fetch the review
        cur.execute("SELECT * FROM reviews WHERE id=?", (review_id,))
        review = cur.fetchone()

        if review:
            # Fetch associated files
            cur.execute("SELECT * FROM files WHERE review_id=?", (review_id,))
            files = cur.fetchall()
            return review, files
        else:
            print("Review not found")
            return None, None
    except Error as e:
        print(f"Error: {e}")
        return None, None


def migrate_database(conn):
    """Add new columns to existing tables if they don't exist"""
    try:
        print("Migrating database...")
        c = conn.cursor()
        # Check if llm_model column exists
        c.execute("PRAGMA table_info(reviews)")
        columns = [column[1] for column in c.fetchall()]

        if "llm_model" not in columns:
            c.execute("ALTER TABLE reviews ADD COLUMN llm_model VARCHAR(100)")
            print("Added llm_model column to reviews table")
        if "github_url_type" not in columns:
            c.execute("ALTER TABLE reviews ADD COLUMN github_url_type VARCHAR(100)")
            print("Added github_url_type column to reviews table")
        conn.commit()
    except Error as e:
        print(f"Migration error: {e}")


def db_init(conn):
    """Create tables and run migrations"""
    if conn is not None:
        create_tables(conn)
        migrate_database(conn)
    else:
        raise Exception("Error! Cannot create the database connection.")
