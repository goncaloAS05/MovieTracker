import os
from dotenv import load_dotenv
import singlestoredb

load_dotenv()

S2_HOST = os.getenv("S2_HOST", "localhost")
S2_PORT = int(os.getenv("S2_PORT", "3306"))
S2_USER = os.getenv("S2_USER", "root")
S2_PASSWORD = os.getenv("S2_PASSWORD", "")
S2_DATABASE = os.getenv("S2_DATABASE")


def get_connection():
    """Return a new singlestoredb connection using environment variables.
    """
    conn = singlestoredb.connect(
        host=S2_HOST,
        port=S2_PORT,
        user=S2_USER,
        password=S2_PASSWORD,
        database=S2_DATABASE,
    )
    try:
        conn.autocommit(True)
    except Exception:
        try:
            conn.autocommit = True
        except Exception:
            pass
    return conn


def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # Drop the old tables so we can recreate them with BIGINTs
    cur.execute("DROP TABLE IF EXISTS watch_status")
    cur.execute("DROP TABLE IF EXISTS titles")

    # Use BIGINT for id and tmdb_id
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS titles (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            tmdb_id BIGINT,
            name VARCHAR(255),
            type VARCHAR(16),
            genre VARCHAR(255),
            release_year INT,
            total_runtime_minutes INT,
            total_seasons INT,
            season_episode_counts TEXT,
            poster_url TEXT
        )
        """
    )

    # Use BIGINT for id, user_id, and title_id
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS watch_status (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            title_id BIGINT NOT NULL,
            status ENUM('want_to_watch','watching','watched') NOT NULL DEFAULT 'want_to_watch',
            rating INT,
            episode_progress INT,
            season_progress INT,
            is_favourite BOOL NOT NULL DEFAULT FALSE,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_watched TIMESTAMP NULL
        )
        """
    )

    cur.close()
    conn.close()
    print("Tables successfully recreated with BIGINT types.")


if __name__ == "__main__":
    create_tables()