import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)


def get_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    kwargs = {}
    if "sslmode=" not in url:
        kwargs["sslmode"] = "require"
    return psycopg.connect(url, **kwargs)


@app.route("/")
def index():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT full_name FROM students ORDER BY full_name, netid"
        ).fetchall()
        averages = conn.execute(
            """
            SELECT
                ROUND(AVG(skill_programming)::numeric, 2),
                ROUND(AVG(skill_data_stats)::numeric, 2),
                ROUND(AVG(skill_frontend_design)::numeric, 2),
                ROUND(AVG(skill_business_pitch)::numeric, 2)
            FROM students
            """
        ).fetchone()
    names = [row[0] for row in rows]
    skill_averages = [
        {"label": "Programming", "value": averages[0]},
        {"label": "Data / stats", "value": averages[1]},
        {"label": "Frontend design", "value": averages[2]},
        {"label": "Business pitch", "value": averages[3]},
    ]
    return render_template("index.html", names=names, skill_averages=skill_averages)


if __name__ == "__main__":
    app.run(debug=True)
