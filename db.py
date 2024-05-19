import sqlite3
from sqlite3 import Error
import uuid

def create_connection(db_file):
    """ Create a database connection to the SQLite database specified by db_file """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"SQLite Database created and connected to {db_file}")
        return conn
    except Error as e:
        print(f"Error: {e}")
    return conn

def create_tables(conn):
    """ Create tables in the SQLite database """
    try:
        sql_create_reviews_table = """
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            github_url TEXT NOT NULL,
            prompt_template TEXT NULL,
            prompt TEXT NULL,
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
        c.execute('''
        CREATE TRIGGER IF NOT EXISTS update_timestamp
        AFTER UPDATE ON reviews
        FOR EACH ROW
        BEGIN
            UPDATE reviews SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        ''')
        # Create an index on the created_at column
        c.execute('''
        CREATE INDEX IF NOT EXISTS idx_created_at ON reviews (created_at)
        ''')
        # Create a trigger to automatically update the updated_at field
        c.execute('''
        CREATE TRIGGER IF NOT EXISTS update_timestamp
        AFTER UPDATE ON files
        FOR EACH ROW
        BEGIN
            UPDATE files SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        ''')
        print("Tables 'reviews' and 'files' created successfully")
    except Error as e:
        print(f"Error: {e}")

def insert_review(conn, name, github_url, prompt_template, prompt):
    """ Insert a new review into the reviews table """
    try:
        review_id = str(uuid.uuid4())
        sql_insert_review = '''INSERT INTO reviews(id, name, github_url, prompt_template, prompt) VALUES(?,?,?,?,?)'''
        cur = conn.cursor()
        cur.execute(sql_insert_review, (review_id, name, github_url, prompt_template, prompt))
        conn.commit()
        print("Review inserted successfully")
        return review_id
    except Error as e:
        print(f"Error: {e}")
        return None

def insert_file(conn, review_id, file_name, diff, code, response):
    """ Insert a new file into the files table """
    try:
        file_id = str(uuid.uuid4())
        sql_insert_file = '''INSERT INTO files(id, review_id, file_name, diff, code, response) VALUES(?,?,?,?,?,?)'''
        cur = conn.cursor()
        cur.execute(sql_insert_file, (file_id, review_id, file_name, diff, code, response))
        conn.commit()
        print("File inserted successfully")
        return file_id
    except Error as e:
        print(f"Error: {e}")
        return None

def delete_review(conn, review_id):
    """ Delete a review and its associated files from the database """
    try:
        sql_delete_files = '''DELETE FROM files WHERE review_id = ?'''
        sql_delete_review = '''DELETE FROM reviews WHERE id = ?'''
        cur = conn.cursor()
        cur.execute(sql_delete_files, (review_id,))
        cur.execute(sql_delete_review, (review_id,))
        conn.commit()
        print("Review and associated files deleted successfully")
    except Error as e:
        print(f"Error: {e}")

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
        print(f"Error: {e}")
        return []


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


def db_init():
    database = r"bin/code_reviews.db"

    # Create a database connection
    conn = create_connection(database)

    # Create tables
    if conn is not None:
        create_tables(conn)
    else:
        print("Error! Cannot create the database connection.")

    # Close the database connection
    if conn:
        conn.close()

if __name__ == '__main__':
    db_init()
