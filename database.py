import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "daily_reports.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


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
                created_at    TEXT    DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS members (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
        """)
        conn.commit()


def save_report(date_str: str, name: str, tasks: str,
                tomorrow_plan: str, impressions: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO reports (date, name, tasks, tomorrow_plan, impressions)"
            " VALUES (?, ?, ?, ?, ?)",
            (date_str, name, tasks, tomorrow_plan, impressions),
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
        sql += " AND (tasks LIKE ? OR tomorrow_plan LIKE ? OR impressions LIKE ?)"
        params.extend([like, like, like])
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


def get_weekly_reports(name: str, start_date, end_date) -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql_query(
            "SELECT date, tasks, tomorrow_plan, impressions"
            " FROM reports"
            " WHERE name=? AND date BETWEEN ? AND ?"
            " ORDER BY date ASC",
            conn,
            params=(name, str(start_date), str(end_date)),
        )


def delete_report(report_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM reports WHERE id=?", (report_id,))
        conn.commit()
