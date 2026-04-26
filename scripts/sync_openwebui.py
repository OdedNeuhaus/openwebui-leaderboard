#!/usr/bin/env python3
"""
Generate leaderboard-data.json from an OpenWebUI database.

This script is meant to run next to a real OpenWebUI deployment or anywhere
that can reach the same database. It currently supports:

- SQLite out of the box
- PostgreSQL when `psycopg` or `psycopg2` is installed

It reads OpenWebUI's `user`, `feedback`, and chat message data and emits a
compact JSON file that the frontend can render directly.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


COLOR_PALETTE = [
    "linear-gradient(135deg, #5cf2c5, #c0ffe9)",
    "linear-gradient(135deg, #f8bc45, #ffe2a1)",
    "linear-gradient(135deg, #67b7ff, #b8dbff)",
    "linear-gradient(135deg, #ff8e72, #ffc3b5)",
    "linear-gradient(135deg, #a08cff, #d8d0ff)",
    "linear-gradient(135deg, #7ef0c0, #d3ffed)",
    "linear-gradient(135deg, #ff8fb2, #ffd6e5)",
    "linear-gradient(135deg, #8bc6ff, #d9eeff)",
]


@dataclass
class UserRow:
    user_id: str
    name: str
    email: str | None
    role: str | None
    last_active_at: int | None


@dataclass
class ChatRow:
    user_id: str
    payload: Any
    created_at: int | None
    updated_at: int | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build leaderboard-data.json from an OpenWebUI database."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("OPENWEBUI_DATABASE_URL"),
        help="OpenWebUI database URL, for example sqlite:////app/backend/data/webui.db or postgresql://user:pass@host/db",
    )
    parser.add_argument(
        "--output",
        default="leaderboard-data.json",
        help="Path to the generated leaderboard JSON file.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Maximum number of rows to emit.",
    )
    parser.add_argument(
        "--active-window-hours",
        type=int,
        default=24,
        help="How far back to consider a user active for the activeToday flag.",
    )
    parser.add_argument(
        "--include-admins",
        action="store_true",
        help="Include admin users in the leaderboard output.",
    )
    return parser.parse_args()


def normalize_sqlite_path(path: str) -> str:
    if path.startswith("sqlite:////"):
        return "/" + path.removeprefix("sqlite:////")
    if path.startswith("sqlite:///"):
        return path.removeprefix("sqlite:///")
    return path


def load_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, memoryview):
        value = value.tobytes().decode("utf-8")
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def connect_postgres(parsed_url):
    try:
        import psycopg  # type: ignore

        conn = psycopg.connect(parsed_url.geturl(), row_factory=psycopg.rows.dict_row)
        return conn, "psycopg"
    except ImportError:
        try:
            import psycopg2  # type: ignore
            import psycopg2.extras  # type: ignore

            conn = psycopg2.connect(parsed_url.geturl())
            return conn, "psycopg2"
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL support requires `psycopg` or `psycopg2` to be installed."
            ) from exc


def fetch_rows(connection, query: str) -> list[dict[str, Any]]:
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    cursor = connection.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()

    if rows and isinstance(rows[0], dict):
        return rows

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def try_fetch_rows(connection, query: str) -> list[dict[str, Any]] | None:
    try:
        return fetch_rows(connection, query)
    except Exception:
        return None


def open_database(database_url: str):
    parsed = urlparse(database_url)

    if parsed.scheme.startswith("sqlite"):
        sqlite_path = normalize_sqlite_path(database_url)
        connection = sqlite3.connect(sqlite_path)
        connection.row_factory = sqlite3.Row
        return connection

    if parsed.scheme in {"postgres", "postgresql"}:
        connection, _driver = connect_postgres(parsed)
        return connection

    raise RuntimeError(
        f"Unsupported database scheme '{parsed.scheme}'. Use sqlite:///... or postgresql://..."
    )


def fetch_users(connection) -> dict[str, UserRow]:
    rows = fetch_rows(
        connection,
        """
        SELECT id, name, email, role, last_active_at
        FROM "user"
        """,
    )

    users = {}
    for row in rows:
        users[row["id"]] = UserRow(
            user_id=row["id"],
            name=row.get("name") or row.get("email") or row["id"],
            email=row.get("email"),
            role=row.get("role"),
            last_active_at=row.get("last_active_at"),
        )
    return users


def fetch_chats(connection) -> list[ChatRow]:
    rows = fetch_rows(
        connection,
        """
        SELECT user_id, chat, created_at, updated_at
        FROM chat
        """,
    )

    chats = []
    for row in rows:
        chats.append(
            ChatRow(
                user_id=row["user_id"],
                payload=load_json_value(row.get("chat")),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    return chats


def fetch_feedback_counts(connection) -> dict[str, int]:
    rows = fetch_rows(
        connection,
        """
        SELECT user_id, COUNT(*) AS feedback_count
        FROM feedback
        GROUP BY user_id
        """,
    )
    return {row["user_id"]: int(row["feedback_count"]) for row in rows}


def fetch_chat_message_rows(connection) -> list[dict[str, Any]] | None:
    # OpenWebUI analytics uses the normalized chat_message table when present.
    return try_fetch_rows(
        connection,
        """
        SELECT user_id, role, created_at
        FROM chat_message
        """,
    )


def extract_history_messages(chat_payload: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(chat_payload, dict):
        return []

    history = chat_payload.get("history")
    if isinstance(history, dict):
        messages = history.get("messages")
        if isinstance(messages, dict):
            return [message for message in messages.values() if isinstance(message, dict)]

    messages = chat_payload.get("messages")
    if isinstance(messages, list):
        return [message for message in messages if isinstance(message, dict)]

    return []


def normalize_timestamp(raw_timestamp: Any) -> int | None:
    if raw_timestamp is None:
        return None

    try:
        timestamp = int(raw_timestamp)
    except (TypeError, ValueError):
        return None

    while timestamp > 10_000_000_000:
        timestamp //= 1000
    return timestamp


def build_message_stats_from_chat_messages(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, set[datetime.date]]]:
    message_counts: dict[str, int] = defaultdict(int)
    activity_dates: dict[str, set[datetime.date]] = defaultdict(set)

    for row in rows:
        if row.get("role") != "assistant":
            continue

        user_id = row.get("user_id")
        if not user_id:
            continue

        message_counts[user_id] += 1

        timestamp = normalize_timestamp(row.get("created_at"))
        if timestamp is None:
            continue

        activity_dates[user_id].add(datetime.fromtimestamp(timestamp, UTC).date())

    return message_counts, activity_dates


def build_message_stats_from_chat_json(
    chats: list[ChatRow],
) -> tuple[dict[str, int], dict[str, set[datetime.date]]]:
    message_counts: dict[str, int] = defaultdict(int)
    activity_dates: dict[str, set[datetime.date]] = defaultdict(set)

    for chat in chats:
        for message in extract_history_messages(chat.payload):
            role = message.get("role")
            if role != "assistant":
                continue

            message_counts[chat.user_id] += 1

            timestamp = normalize_timestamp(message.get("timestamp"))
            if timestamp is None:
                continue

            activity_dates[chat.user_id].add(datetime.fromtimestamp(timestamp, UTC).date())

    return message_counts, activity_dates


def build_message_stats(connection) -> tuple[dict[str, int], dict[str, set[datetime.date]]]:
    chat_message_rows = fetch_chat_message_rows(connection)
    if chat_message_rows:
        return build_message_stats_from_chat_messages(chat_message_rows)

    chats = fetch_chats(connection)
    return build_message_stats_from_chat_json(chats)


def compute_streak(dates: set[datetime.date]) -> int:
    if not dates:
        return 0

    streak = 0
    current_day = max(dates)

    while current_day in dates:
        streak += 1
        current_day -= timedelta(days=1)

    return streak


def build_leaderboard_entries(
    users: dict[str, UserRow],
    message_counts: dict[str, int],
    feedback_counts: dict[str, int],
    activity_dates: dict[str, set[datetime.date]],
    active_window_hours: int,
    include_admins: bool,
    top: int,
) -> list[dict[str, Any]]:
    threshold = int((datetime.now(UTC) - timedelta(hours=active_window_hours)).timestamp())
    rows: list[dict[str, Any]] = []

    ordered_users = sorted(
        users.values(),
        key=lambda user: (
            message_counts.get(user.user_id, 0) + feedback_counts.get(user.user_id, 0),
            message_counts.get(user.user_id, 0),
            user.name.lower(),
        ),
        reverse=True,
    )

    palette_index = 0

    for user in ordered_users:
        if not include_admins and user.role == "admin":
            continue

        messages = int(message_counts.get(user.user_id, 0))
        feedbacks = int(feedback_counts.get(user.user_id, 0))

        if messages == 0 and feedbacks == 0:
            continue

        streak = compute_streak(activity_dates.get(user.user_id, set()))
        last_active_at = user.last_active_at or 0
        active_today = last_active_at >= threshold

        rows.append(
            {
                "name": user.name,
                "messages": messages,
                "feedbacks": feedbacks,
                "streak": streak,
                "activeToday": active_today,
                "color": COLOR_PALETTE[palette_index % len(COLOR_PALETTE)],
                "email": user.email,
                "role": user.role,
                "lastActiveAt": last_active_at,
            }
        )
        palette_index += 1

        if len(rows) >= top:
            break

    return rows


def main() -> int:
    args = parse_args()

    if not args.database_url:
        print(
            "Missing database URL. Pass --database-url or set OPENWEBUI_DATABASE_URL.",
            file=sys.stderr,
        )
        return 1

    connection = open_database(args.database_url)

    try:
        users = fetch_users(connection)
        feedback_counts = fetch_feedback_counts(connection)
        message_counts, activity_dates = build_message_stats(connection)

        leaderboard_rows = build_leaderboard_entries(
            users=users,
            message_counts=message_counts,
            feedback_counts=feedback_counts,
            activity_dates=activity_dates,
            active_window_hours=args.active_window_hours,
            include_admins=args.include_admins,
            top=args.top,
        )

        output_path = Path(args.output)
        output_path.write_text(
            json.dumps(leaderboard_rows, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(
            f"Wrote {len(leaderboard_rows)} leaderboard rows to {output_path}",
            file=sys.stderr,
        )
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
