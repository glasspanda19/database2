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
        raise RuntimeError("DATABASE_URL is missing from .env")
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
    names = [row[0] for row in rows]
    return render_template("index.html", names=names)


if __name__ == "__main__":
    app.run(debug=True)
