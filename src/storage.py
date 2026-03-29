"""SQLite storage layer for activities and signups.

This module replaces in-memory dictionaries with persistent storage while
preserving the API response shape used by the frontend.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "activities.db"
SCHEMA_VERSION = 1


SEED_ACTIVITIES: Dict[str, Dict[str, object]] = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


class ActivityNotFoundError(Exception):
    """Raised when an activity name does not exist."""


class DuplicateSignupError(Exception):
    """Raised when a student is already signed up for an activity."""


class MissingSignupError(Exception):
    """Raised when a student is not signed up for an activity."""


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create schema and seed data on first run."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL CHECK (max_participants > 0)
            );

            CREATE TABLE IF NOT EXISTS signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(activity_id, email),
                FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE
            );
            """
        )

        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )

        count = conn.execute("SELECT COUNT(*) AS total FROM activities").fetchone()["total"]
        if count == 0:
            _seed_data(conn)


def _seed_data(conn: sqlite3.Connection) -> None:
    for name, details in SEED_ACTIVITIES.items():
        cursor = conn.execute(
            """
            INSERT INTO activities (name, description, schedule, max_participants)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                str(details["description"]),
                str(details["schedule"]),
                int(details["max_participants"]),
            ),
        )
        activity_id = cursor.lastrowid

        participants = details.get("participants", [])
        for email in participants:
            conn.execute(
                "INSERT INTO signups (activity_id, email) VALUES (?, ?)",
                (activity_id, str(email)),
            )


def _get_activity(conn: sqlite3.Connection, activity_name: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, name, description, schedule, max_participants FROM activities WHERE name = ?",
        (activity_name,),
    ).fetchone()


def list_activities() -> Dict[str, Dict[str, object]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, description, schedule, max_participants FROM activities ORDER BY name"
        ).fetchall()

        signup_rows = conn.execute(
            "SELECT activity_id, email FROM signups ORDER BY id"
        ).fetchall()

    participants_by_activity: Dict[int, List[str]] = {}
    for row in signup_rows:
        participants_by_activity.setdefault(int(row["activity_id"]), []).append(row["email"])

    result: Dict[str, Dict[str, object]] = {}
    for row in rows:
        activity_id = int(row["id"])
        result[row["name"]] = {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": int(row["max_participants"]),
            "participants": participants_by_activity.get(activity_id, []),
        }

    return result


def signup_for_activity(activity_name: str, email: str) -> None:
    with _connect() as conn:
        activity = _get_activity(conn, activity_name)
        if activity is None:
            raise ActivityNotFoundError()

        try:
            conn.execute(
                "INSERT INTO signups (activity_id, email) VALUES (?, ?)",
                (int(activity["id"]), email),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateSignupError() from exc


def unregister_from_activity(activity_name: str, email: str) -> None:
    with _connect() as conn:
        activity = _get_activity(conn, activity_name)
        if activity is None:
            raise ActivityNotFoundError()

        cursor = conn.execute(
            "DELETE FROM signups WHERE activity_id = ? AND email = ?",
            (int(activity["id"]), email),
        )
        if cursor.rowcount == 0:
            raise MissingSignupError()
