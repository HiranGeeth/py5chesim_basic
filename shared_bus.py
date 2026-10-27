"""Shared data bus using SQLite to avoid Windows file locks."""
import sqlite3
import json
import os

DB_FILE = "shared/live_bus.db"

def _get_conn():
    os.makedirs("shared", exist_ok=True)
    # timeout=1.0 means "wait up to 1 second for the lock to clear"
    conn = sqlite3.connect(DB_FILE, timeout=1.0)
    # Create table if it doesn't exist
    conn.execute("CREATE TABLE IF NOT EXISTS state (section TEXT PRIMARY KEY, data TEXT)")
    return conn

def read_state():
    """Reads the entire state as a dictionary."""
    state = {}
    try:
        with _get_conn() as conn:
            for row in conn.execute("SELECT section, data FROM state"):
                state[row[0]] = json.loads(row[1])
    except sqlite3.OperationalError as e:
        print(f"[bus] read warning: {e}")
    return state

def update_section(section_name, data):
    """Updates just one section (e.g. 'classifier') safely."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO state (section, data) VALUES (?, ?)",
                (section_name, json.dumps(data))
            )
    except sqlite3.OperationalError as e:
        # If it's locked, we just skip this update. Next frame will catch it.
        pass