import sqlite3
from datetime import datetime


DB_PATH = "food_bot.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def add_products(user_id: int, products: list[str]):
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO products (user_id, product, added_at) VALUES (?, ?, ?)",
            [(user_id, p.strip(), datetime.now()) for p in products if p.strip()]
        )
        conn.commit()


def get_products(user_id: int) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT product FROM products WHERE user_id = ? ORDER BY added_at",
            (user_id,)
        ).fetchall()
    return [row["product"] for row in rows]


def clear_products(user_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM products WHERE user_id = ?", (user_id,))
        conn.commit()
