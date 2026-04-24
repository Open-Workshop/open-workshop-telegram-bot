from __future__ import annotations

import sqlite3
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "bot_statistics.sqlite3"
_LOCK = threading.Lock()
_COUNTERS = (
    "incoming",
    "help_command",
    "project_command",
    "statistics_command",
    "graph_command",
    "download_attempt",
    "download_success",
    "download_fail",
    "invalid_input",
)


def configure(db_path: str | Path | None = None, *, base_dir: Path | None = None) -> None:
    global DB_PATH
    if not db_path:
        return

    resolved = Path(db_path).expanduser()
    if not resolved.is_absolute() and base_dir is not None:
        resolved = Path(base_dir) / resolved

    DB_PATH = resolved.resolve()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def _today_key() -> str:
    return datetime.now().astimezone().date().isoformat()


def init_db() -> None:
    columns_sql = ",\n        ".join(f"{column} INTEGER NOT NULL DEFAULT 0" for column in _COUNTERS)
    with _LOCK:
        with _connect() as connection:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    day TEXT PRIMARY KEY,
                    {columns_sql}
                )
                """
            )


def record_counts(**counters: int) -> None:
    payload = {counter: max(0, int(counters.get(counter, 0) or 0)) for counter in _COUNTERS}
    if not any(payload.values()):
        return

    columns_sql = ", ".join(_COUNTERS)
    placeholders = ", ".join("?" for _ in _COUNTERS)
    updates_sql = ", ".join(f"{column} = {column} + excluded.{column}" for column in _COUNTERS)
    values = [_today_key(), *[payload[column] for column in _COUNTERS]]

    with _LOCK:
        with _connect() as connection:
            connection.execute(
                f"""
                INSERT INTO daily_stats (day, {columns_sql})
                VALUES (?, {placeholders})
                ON CONFLICT(day) DO UPDATE SET {updates_sql}
                """,
                values,
            )


def get_totals() -> dict[str, int | str | None]:
    summary_sql = ",\n        ".join(
        f"COALESCE(SUM({column}), 0) AS {column}" for column in _COUNTERS
    )
    with _LOCK:
        with _connect() as connection:
            row = connection.execute(
                f"""
                SELECT
                    {summary_sql},
                    COUNT(*) AS active_days,
                    MIN(day) AS first_day,
                    MAX(day) AS last_day
                FROM daily_stats
                """
            ).fetchone()
    return dict(row)


def get_day(day_key: str | None = None) -> dict[str, int | str]:
    day_key = day_key or _today_key()
    columns_sql = ", ".join(_COUNTERS)

    with _LOCK:
        with _connect() as connection:
            row = connection.execute(
                f"SELECT day, {columns_sql} FROM daily_stats WHERE day = ?",
                (day_key,),
            ).fetchone()

    if row is None:
        return {"day": day_key, **{column: 0 for column in _COUNTERS}}

    return dict(row)


def get_recent(days: int = 14) -> list[dict[str, int | str]]:
    days = max(1, days)
    columns_sql = ", ".join(_COUNTERS)

    with _LOCK:
        with _connect() as connection:
            rows = connection.execute(
                f"SELECT day, {columns_sql} FROM daily_stats ORDER BY day DESC LIMIT ?",
                (days,),
            ).fetchall()

    return [dict(row) for row in reversed(rows)]


def get_filled_history(days: int = 14) -> list[dict[str, int | str]]:
    days = max(1, days)
    existing_rows = {row["day"]: row for row in get_recent(days)}
    today = date.today()
    history: list[dict[str, int | str]] = []

    for offset in range(days - 1, -1, -1):
        day_key = (today - timedelta(days=offset)).isoformat()
        row = {"day": day_key, **{column: 0 for column in _COUNTERS}}
        row.update(existing_rows.get(day_key, {}))
        history.append(row)

    return history
