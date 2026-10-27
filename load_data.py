"""Apply schema.sql and load class_dataset.csv into DATABASE_URL."""

from __future__ import annotations

import csv
from pathlib import Path

import psycopg
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent
KNOWN_TOOLS = {"Python", "SQL", "JavaScript", "Excel", "R"}
DAY_GROUPS = {"Weekday", "Weekend"}
TIMES = {"mornings", "afternoons", "evenings"}


def parse_availability(raw: str) -> list[tuple[str, str]]:
    slots: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for part in raw.split(";"):
        token = " ".join(part.split())
        if not token:
            continue
        day, _, time = token.partition(" ")
        time = time.strip().lower()
        if day not in DAY_GROUPS or time not in TIMES:
            raise ValueError(f"Unrecognized availability token: {token!r}")
        key = (day, time)
        if key not in seen:
            seen.add(key)
            slots.append(key)
    return slots


def parse_tools(raw: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for part in raw.split(";"):
        name = part.strip()
        if not name or name.lower() == "none yet":
            continue
        if name not in KNOWN_TOOLS:
            raise ValueError(f"Unrecognized tool: {name!r}")
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def main() -> None:
    load_dotenv(ROOT / ".env")
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing from .env")

    schema_sql = (ROOT / "schema.sql").read_text(encoding="utf-8")
    with (ROOT / "class_dataset.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    connect_kw: dict = {}
    if "sslmode=" not in url:
        connect_kw["sslmode"] = "require"

    with psycopg.connect(url, **connect_kw) as conn:
        conn.execute("SET client_min_messages TO WARNING")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
            existing = [r[0] for r in cur.fetchall()]

            # Redeploy: drop prior objects from this schema so CREATE TYPE succeeds.
            if existing:
                cur.execute("DROP TABLE IF EXISTS student_availability, student_tools, students, availability_slots, tools CASCADE")
                cur.execute("DROP TYPE IF EXISTS school_year_t, intro_programming_t, day_group_t, time_of_day_t")

            cur.execute(schema_sql)

            cur.execute("SELECT tool_name, tool_id FROM tools")
            tool_ids = dict(cur.fetchall())
            cur.execute("SELECT day_group::text, time_of_day::text, slot_id FROM availability_slots")
            slot_ids = {(day, time): slot_id for day, time, slot_id in cur.fetchall()}

            student_sql = """
                INSERT INTO students (
                    netid, full_name, school_year, intro_programming,
                    skill_programming, skill_data_stats, skill_frontend_design,
                    skill_business_pitch, working_style, interests, semester_goal,
                    submitted_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            students = [
                (
                    row["netid"].strip(),
                    row["name"].strip(),
                    row["school_year"].strip(),
                    row["intro_programming"].strip(),
                    int(row["skill_programming"]),
                    int(row["skill_data_stats"]),
                    int(row["skill_frontend_design"]),
                    int(row["skill_business_pitch"]),
                    row["working_style"],
                    row["interests"],
                    row["semester_goal"],
                    row["submitted_at"].strip(),
                )
                for row in rows
            ]
            cur.executemany(student_sql, students)

            tool_links = []
            avail_links = []
            for row in rows:
                netid = row["netid"].strip()
                for tool in parse_tools(row["tools"]):
                    tool_links.append((netid, tool_ids[tool]))
                for day, time in parse_availability(row["availability"]):
                    avail_links.append((netid, slot_ids[(day, time)]))

            cur.executemany(
                "INSERT INTO student_tools (netid, tool_id) VALUES (%s, %s)",
                tool_links,
            )
            cur.executemany(
                "INSERT INTO student_availability (netid, slot_id) VALUES (%s, %s)",
                avail_links,
            )

            counts = {}
            for table in (
                "students",
                "tools",
                "availability_slots",
                "student_tools",
                "student_availability",
            ):
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]

        conn.commit()

    print("Deployed:")
    for table, n in counts.items():
        print(f"  {table}: {n}")


if __name__ == "__main__":
    main()
