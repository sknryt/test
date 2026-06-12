import hashlib
import secrets
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "daily_reports.db"

# 初期管理者アカウント
DEFAULT_ADMIN_USERNAME = "坂野諒太"
DEFAULT_ADMIN_PASSWORD = "MonsterEnergy11!"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS reports (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                date          TEXT    NOT NULL,
                name          TEXT    NOT NULL,
                tasks         TEXT    NOT NULL,
                tomorrow_plan TEXT    NOT NULL,
                impressions   TEXT    DEFAULT '',
                questions     TEXT    DEFAULT '',
                work_hours    REAL    DEFAULT 0,
                start_time    TEXT    DEFAULT '',
                end_time      TEXT    DEFAULT '',
                created_at    TEXT    DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS members (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                salt          TEXT    NOT NULL,
                is_admin      INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT    DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                username   TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        """)
        conn.commit()

        # 既存DBに不足している列があれば追加（マイグレーション）
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(reports)").fetchall()]
        if "work_hours" not in cols:
            conn.execute("ALTER TABLE reports ADD COLUMN work_hours REAL DEFAULT 0")
        if "start_time" not in cols:
            conn.execute("ALTER TABLE reports ADD COLUMN start_time TEXT DEFAULT ''")
        if "end_time" not in cols:
            conn.execute("ALTER TABLE reports ADD COLUMN end_time TEXT DEFAULT ''")
        if "questions" not in cols:
            conn.execute("ALTER TABLE reports ADD COLUMN questions TEXT DEFAULT ''")
        conn.commit()

    # 初期管理者アカウントを作成（未登録の場合のみ）
    if not user_exists(DEFAULT_ADMIN_USERNAME):
        create_user(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, is_admin=True)
        add_member(DEFAULT_ADMIN_USERNAME)


def save_report(date_str: str, name: str, tasks: str,
                tomorrow_plan: str, impressions: str, work_hours: float = 0.0,
                start_time: str = "", end_time: str = "", questions: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO reports"
            " (date, name, tasks, tomorrow_plan, impressions, questions,"
            "  work_hours, start_time, end_time)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (date_str, name, tasks, tomorrow_plan, impressions, questions,
             work_hours, start_time, end_time),
        )
        conn.execute("INSERT OR IGNORE INTO members (name) VALUES (?)", (name,))
        conn.commit()


def has_submitted(name: str, date_str: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE name=? AND date=?",
            (name, date_str),
        )
        return cur.fetchone()[0] > 0


def get_reports(date_from=None, date_to=None,
                name=None, keyword=None) -> pd.DataFrame:
    sql = "SELECT * FROM reports WHERE 1=1"
    params: list = []
    if date_from:
        sql += " AND date >= ?"
        params.append(str(date_from))
    if date_to:
        sql += " AND date <= ?"
        params.append(str(date_to))
    if name:
        sql += " AND name = ?"
        params.append(name)
    if keyword:
        like = f"%{keyword}%"
        sql += " AND (tasks LIKE ? OR tomorrow_plan LIKE ? OR impressions LIKE ? OR questions LIKE ?)"
        params.extend([like, like, like, like])
    sql += " ORDER BY date DESC, created_at DESC"
    with _connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_all_reports() -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql_query(
            "SELECT * FROM reports ORDER BY date DESC, created_at DESC", conn
        )


def get_members() -> list:
    with _connect() as conn:
        cur = conn.execute("SELECT name FROM members ORDER BY name")
        return [r[0] for r in cur.fetchall()]


def add_member(name: str) -> None:
    with _connect() as conn:
        conn.execute("INSERT OR IGNORE INTO members (name) VALUES (?)", (name,))
        conn.commit()


def delete_member(name: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM members WHERE name=?", (name,))
        conn.commit()


def get_today_submitters(date_str: str) -> list:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT DISTINCT name FROM reports WHERE date=?", (date_str,)
        )
        return [r[0] for r in cur.fetchall()]


def get_submission_stats(start_date=None, end_date=None) -> pd.DataFrame:
    sql = "SELECT date, name FROM reports WHERE 1=1"
    params: list = []
    if start_date:
        sql += " AND date >= ?"
        params.append(str(start_date))
    if end_date:
        sql += " AND date <= ?"
        params.append(str(end_date))
    with _connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def delete_report(report_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM reports WHERE id=?", (report_id,))
        conn.commit()


# ─── ユーザー認証 ──────────────────────────────────────────────────────────────
def user_exists(username: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("SELECT 1 FROM users WHERE username=?", (username,))
        return cur.fetchone() is not None


def create_user(username: str, password: str, is_admin: bool = False) -> bool:
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    with _connect() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, is_admin)"
                " VALUES (?, ?, ?, ?)",
                (username, pw_hash, salt, int(is_admin)),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def verify_user(username: str, password: str):
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
    if row is None:
        return None
    if _hash_password(password, row["salt"]) != row["password_hash"]:
        return None
    return {"username": row["username"], "is_admin": bool(row["is_admin"])}


def get_users() -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql_query(
            "SELECT username, is_admin, created_at FROM users ORDER BY username", conn
        )


def update_password(username: str, new_password: str) -> None:
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(new_password, salt)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash=?, salt=? WHERE username=?",
            (pw_hash, salt, username),
        )
        # パスワード変更時は既存のログインセッションを無効化
        conn.execute("DELETE FROM sessions WHERE username=?", (username,))
        conn.commit()


# ─── ログインセッション ────────────────────────────────────────────────────────
def create_session(username: str, days: int = 7) -> str:
    token = secrets.token_urlsafe(32)
    with _connect() as conn:
        # 期限切れセッションを掃除してから発行
        conn.execute("DELETE FROM sessions WHERE expires_at < datetime('now', 'localtime')")
        conn.execute(
            "INSERT INTO sessions (token, username, expires_at)"
            " VALUES (?, ?, datetime('now', 'localtime', ?))",
            (token, username, f"+{days} days"),
        )
        conn.commit()
    return token


def get_session_user(token: str):
    with _connect() as conn:
        row = conn.execute(
            "SELECT s.username, u.is_admin"
            " FROM sessions s JOIN users u ON u.username = s.username"
            " WHERE s.token=? AND s.expires_at >= datetime('now', 'localtime')",
            (token,),
        ).fetchone()
    if row is None:
        return None
    return {"username": row["username"], "is_admin": bool(row["is_admin"])}


def delete_session(token: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()


def set_admin(username: str, is_admin: bool) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET is_admin=? WHERE username=?", (int(is_admin), username)
        )
        conn.commit()


def delete_user(username: str) -> None:
    """アカウントを削除し、そのユーザーの日報・メンバー登録・セッションもすべて削除する。"""
    with _connect() as conn:
        conn.execute("DELETE FROM users WHERE username=?", (username,))
        conn.execute("DELETE FROM reports WHERE name=?", (username,))
        conn.execute("DELETE FROM members WHERE name=?", (username,))
        conn.execute("DELETE FROM sessions WHERE username=?", (username,))
        conn.commit()
