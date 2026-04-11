import sqlite3
import time
from datetime import datetime

DB_NAME = 'guardian_drive.db'


def init_db():
    """Initializes the database. Removed DROP TABLE to persist logs between restarts."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    # Removed DROP TABLE so your history stays saved for the judges!
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs
                      (
                          id
                          INTEGER
                          PRIMARY
                          KEY
                          AUTOINCREMENT,
                          type
                          TEXT,
                          timestamp
                          TEXT,
                          unix_time
                          REAL
                      )''')
    conn.commit()
    conn.close()


def log_event(event_type):
    """Logs an event with both a readable timestamp and a unix float for math."""
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        unix_now = time.time()

        conn.execute("INSERT INTO logs (type, timestamp, unix_time) VALUES (?, ?, ?)",
                     (event_type, now, unix_now))
        conn.commit()
        conn.close()
        print(f"DEBUG: Logged {event_type} at {now}")  # Helps you verify in the terminal
    except Exception as e:
        print(f"DATABASE ERROR: {e}")


def get_event_frequency(event_type, seconds=300):
    """Checks frequency based on unix_time."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    limit = time.time() - seconds
    cursor.execute("SELECT COUNT(*) FROM logs WHERE type=? AND unix_time > ?", (event_type, limit))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def reset_yawn_history():
    """Manual wipe for the recovery logic."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("DELETE FROM logs")
    conn.commit()
    conn.close()