"""
AI-Powered Mental Health Chat Assistant
----------------------------------------
Flask + Gemini API chat app with a rule-based crisis-safety layer.

IMPORTANT: This is a portfolio/educational project, NOT a clinical tool.
The safety layer intercepts crisis language BEFORE it reaches the LLM
response path, so the model never has to "handle" an acute crisis alone.
"""

import os
import sqlite3
import uuid
from datetime import datetime

from flask import Flask, request, jsonify, session, render_template
import google.generativeai as genai

from safety import check_for_crisis, CRISIS_RESPONSE
from prompts import SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Set the GEMINI_API_KEY environment variable before running.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT,
)

DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,           -- 'user' or 'assistant'
            content TEXT NOT NULL,
            flagged INTEGER DEFAULT 0,    -- 1 if crisis layer triggered
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


# Run at import time so the table exists whether the app is started with
# `python app.py` (local dev) or `gunicorn app:app` (production) — gunicorn
# never executes the __main__ block below.
init_db()


def save_message(session_id, role, content, flagged=0):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO messages (session_id, role, content, flagged, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, flagged, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(session_id, limit=20):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    return list(reversed(rows))  # oldest first


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    session_id = session.get("session_id") or str(uuid.uuid4())
    session["session_id"] = session_id

    # ---- SAFETY LAYER: runs BEFORE any LLM call ----
    is_crisis, matched_category = check_for_crisis(user_message)

    save_message(session_id, "user", user_message, flagged=int(is_crisis))

    if is_crisis:
        # Never let the LLM freestyle a response to acute crisis language.
        reply = CRISIS_RESPONSE
        save_message(session_id, "assistant", reply, flagged=1)
        return jsonify({
            "reply": reply,
            "flagged": True,
            "category": matched_category,
        })

    # ---- Normal path: build context + call Gemini ----
    history = get_history(session_id, limit=20)
    gemini_history = [
        {"role": "user" if r == "user" else "model", "parts": [c]}
        for r, c in history[:-1]  # exclude the message we're about to send
    ]

    try:
        chat_session = model.start_chat(history=gemini_history)
        response = chat_session.send_message(user_message)
        reply = response.text
    except Exception as exc:  # keep the demo resilient
        reply = (
            "I'm having trouble responding right now. "
            "If this is urgent, please reach out to a crisis line or someone you trust."
        )
        app.logger.error("Gemini API error: %s", exc)

    save_message(session_id, "assistant", reply, flagged=0)

    return jsonify({"reply": reply, "flagged": False})


@app.route("/api/history", methods=["GET"])
def history():
    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"messages": []})
    rows = get_history(session_id, limit=100)
    return jsonify({"messages": [{"role": r, "content": c} for r, c in rows]})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
