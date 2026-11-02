import sqlite3
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zepto_bot.db")


DEFAULT_PRICE_PER_SLIDE = 5000
INITIAL_FREE_SLIDES = 3
INITIAL_USER_BALANCE = DEFAULT_PRICE_PER_SLIDE * INITIAL_FREE_SLIDES  # 15 000 so'm (3 ta bepul slayd)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Ma'lumotlar bazasi jadvallarini yaratish va eski balanslarni yangilash."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Foydalanuvchilar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance INTEGER DEFAULT 15000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # To'lovlar va cheklar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER DEFAULT 5000,
                photo_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Sozlamalar jadvali (admin ID va h.k.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Eski balanslarni yangi pul tizimiga o'tkazish (agar < 5000 so'm bo'lsa, 15 000 so'm qilib belgilaymiz)
        cursor.execute("UPDATE users SET balance = ? WHERE balance < ?", (INITIAL_USER_BALANCE, DEFAULT_PRICE_PER_SLIDE))
        
        conn.commit()
    logger.info("Ma'lumotlar bazasi (SQLite) muvaffaqiyatli ishga tushdi.")


def get_or_create_user(user_id: int, username: Optional[str] = None, full_name: Optional[str] = None) -> Dict[str, Any]:
    """Foydalanuvchini olish yoki yangi foydalanuvchi yaratish (3 ta bepul taqdimot = 15 000 so'm)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            # Yangilash
            cursor.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username or "", full_name or "", user_id)
            )
            conn.commit()
            return dict(row)
        else:
            # Yangi foydalanuvchi: 3 ta bepul taqdimot sovg'a (15 000 so'm)
            cursor.execute(
                "INSERT INTO users (user_id, username, full_name, balance) VALUES (?, ?, ?, ?)",
                (user_id, username or "", full_name or "", INITIAL_USER_BALANCE)
            )
            conn.commit()
            return {
                "user_id": user_id,
                "username": username or "",
                "full_name": full_name or "",
                "balance": INITIAL_USER_BALANCE
            }


def get_balance(user_id: int) -> int:
    """Foydalanuvchi balansini olish."""
    user = get_or_create_user(user_id)
    return user.get("balance", 0)


def add_balance(user_id: int, amount: int = 5000) -> int:
    """Foydalanuvchi balansini oshirish (so'mda)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row["balance"] if row else 0


def deduct_balance(user_id: int, amount: int = 5000) -> bool:
    """Foydalanuvchi balansidan yechish (so'mda)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or row["balance"] < amount:
            return False
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        return True


def create_payment(user_id: int, photo_file_id: str, amount: int = 5000) -> int:
    """Yangi to'lov cheki yozuvini yaratish."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO payments (user_id, amount, photo_file_id, status) VALUES (?, ?, ?, 'pending')",
            (user_id, amount, photo_file_id)
        )
        conn.commit()
        return cursor.lastrowid


def get_payment(payment_id: int) -> Optional[Dict[str, Any]]:
    """To'lov ma'lumotlarini olish."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def approve_payment(payment_id: int, amount: int = 5000) -> Optional[int]:
    """To'lovni tasdiqlash va balansga qo'shish."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        payment = cursor.fetchone()
        if not payment or payment["status"] != "pending":
            return None
        
        user_id = payment["user_id"]
        cursor.execute("UPDATE payments SET status = 'approved', amount = ? WHERE id = ?", (amount, payment_id))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        return user_id


def reject_payment(payment_id: int) -> Optional[int]:
    """To'lovni rad etish."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        payment = cursor.fetchone()
        if not payment or payment["status"] != "pending":
            return None
        
        user_id = payment["user_id"]
        cursor.execute("UPDATE payments SET status = 'rejected' WHERE id = ?", (payment_id,))
        conn.commit()
        return user_id


def get_users_count() -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        row = cursor.fetchone()
        return row[0] if row else 0


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
