"""
memory.py - Rubia的记忆系统
- 短期记忆：SQLite对话历史
- 长期记忆：ChromaDB向量数据库
- 朋友圈动态：SQLite moments表
"""

import sqlite3
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions

DB_PATH = "rubia_memory.db"
CHROMA_PATH = "./chroma_db"

# ── 初始化 ───────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS moments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            mood TEXT DEFAULT '',
            tag TEXT DEFAULT '',
            likes INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# ── 短期记忆 ─────────────────────────────────────────────────────

def save_message(role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
        (role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_recent_messages(limit: int = 20) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def get_all_messages() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content, timestamp FROM messages ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]

def clear_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

# ── 长期记忆 ─────────────────────────────────────────────────────

def get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.DefaultEmbeddingFunction()
    return client.get_or_create_collection(name="rubia_longterm", embedding_function=ef)

def save_long_term_memory(summary: str):
    collection = get_chroma_collection()
    doc_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    collection.add(
        documents=[summary],
        ids=[doc_id],
        metadatas=[{"timestamp": datetime.now().isoformat()}]
    )
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO long_term_memory (summary, timestamp) VALUES (?, ?)",
              (summary, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def retrieve_relevant_memories(query: str, n_results: int = 3) -> list[str]:
    collection = get_chroma_collection()
    if collection.count() == 0:
        return []
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count())
    )
    return results["documents"][0] if results["documents"] else []

def get_all_long_term_memories() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT summary, timestamp FROM long_term_memory ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [{"summary": r[0], "timestamp": r[1]} for r in rows]

# ── 朋友圈动态 ──────────────────────────────────────────────────

def save_moment(content: str, mood: str = "", tag: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO moments (content, mood, tag, likes, timestamp) VALUES (?, ?, ?, 0, ?)",
        (content, mood, tag, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_moments(limit: int = 30) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, content, mood, tag, likes, timestamp FROM moments ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "content": r[1], "mood": r[2], "tag": r[3], "likes": r[4], "timestamp": r[5]}
        for r in rows
    ]

def like_moment(moment_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE moments SET likes = likes + 1 WHERE id = ?", (moment_id,))
    conn.commit()
    c.execute("SELECT likes FROM moments WHERE id = ?", (moment_id,))
    likes = c.fetchone()[0]
    conn.close()
    return likes

def get_today_moment_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM moments WHERE timestamp LIKE ?", (f"{today}%",))
    count = c.fetchone()[0]
    conn.close()
    return count