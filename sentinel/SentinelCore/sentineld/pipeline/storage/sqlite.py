import sqlite3
import time
import uuid

DB = "sentinel.db"

def init():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS transcripts (
        id TEXT PRIMARY KEY,
        timestamp INTEGER,
        text TEXT,
        embedding BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS actions (
        id TEXT PRIMARY KEY,
        timestamp INTEGER,
        type TEXT,
        title TEXT,
        confidence REAL
    )""")

    conn.commit()
    conn.close()

def save_transcript(text, embedding):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transcripts VALUES (?,?,?,?)",
        (str(uuid.uuid4()), int(time.time()), text, embedding)
    )
    conn.commit()
    conn.close()

def save_actions(actions):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    for a in actions:
        cur.execute(
            "INSERT INTO actions VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), int(time.time()), a["type"], a["title"], a.get("confidence", 0.5))
        )
    conn.commit()
    conn.close()
