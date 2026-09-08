"""
AI-Powered Mental Health Chat Assistant
----------------------------------------
Flask + Gemini API chat app with a rule-based crisis-safety layer,
plus basic username/password accounts so each user gets their own
private chat history.

IMPORTANT: This is a portfolio/educational project, NOT a clinical tool.
"""

import os
import sqlite3
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
from google.genai import types

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

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3.6-flash"

chat_config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
)

DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            flagged INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


init_db()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Not logged in"}), 401
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def get_user_by_username(username):
    conn = sqlite3.connect(DB_PATH)

    row = conn.execute(
        """
        SELECT id, username, password_hash
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()

    conn.close()
    return row


def create_user(username, password):
    now = datetime.utcnow().isoformat()
    password_hash = generate_password_hash(password)

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        INSERT INTO users (username, password_hash, created_at)
        VALUES (?, ?, ?)
        """,
        (username, password_hash, now),
    )

    conn.commit()
    user_id = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()[0]
    conn.close()

    return user_id


# ---------------------------------------------------------------------------
# Conversation helpers (scoped to a user)
# ---------------------------------------------------------------------------

def create_conversation(user_id):
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        INSERT INTO conversations
        (session_id, user_id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, user_id, "New Chat", now, now),
    )

    conn.commit()
    conn.close()

    return session_id


def conversation_belongs_to_user(session_id, user_id):
    conn = sqlite3.connect(DB_PATH)

    row = conn.execute(
        """
        SELECT 1 FROM conversations
        WHERE session_id = ? AND user_id = ?
        """,
        (session_id, user_id),
    ).fetchone()

    conn.close()
    return bool(row)


def delete_conversation(session_id):
    conn = sqlite3.connect(DB_PATH)

    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))

    conn.commit()
    conn.close()


def save_message(session_id, role, content, flagged=0):
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        INSERT INTO messages
        (session_id, role, content, flagged, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session_id,
            role,
            content,
            flagged,
            datetime.utcnow().isoformat(),
        ),
    )

    conn.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE session_id = ?
        """,
        (datetime.utcnow().isoformat(), session_id),
    )

    # Use the first user message as the conversation title.
    if role == "user":
        row = conn.execute(
            """
            SELECT title FROM conversations
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

        if row and row[0] == "New Chat":
            title = content[:40].strip()

            if len(content) > 40:
                title += "..."

            conn.execute(
                """
                UPDATE conversations
                SET title = ?
                WHERE session_id = ?
                """,
                (title or "New Chat", session_id),
            )

    conn.commit()
    conn.close()


def get_history(session_id, limit=100):
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        """
        SELECT role, content, flagged, created_at
        FROM messages
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()

    conn.close()

    return rows


def delete_conversation(session_id, user_id):
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        DELETE FROM messages
        WHERE session_id = ?
        """,
        (session_id,),
    )

    conn.execute(
        """
        DELETE FROM conversations
        WHERE session_id = ? AND user_id = ?
        """,
        (session_id, user_id),
    )

    conn.commit()
    conn.close()


def get_conversations(user_id):
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        """
        SELECT session_id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (user_id,),
    ).fetchall()

    conn.close()

    return rows


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", error=None)

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if not username or not password:
        return render_template(
            "signup.html",
            error="Please enter a username and password.",
        )

    if get_user_by_username(username):
        return render_template(
            "signup.html",
            error="That username is already taken.",
        )

    user_id = create_user(username, password)
    session["user_id"] = user_id
    session["username"] = username

    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    row = get_user_by_username(username)

    if not row or not check_password_hash(row[2], password):
        return render_template(
            "login.html",
            error="Incorrect username or password.",
        )

    session["user_id"] = row[0]
    session["username"] = row[1]

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# App routes
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def index():
    # Every fresh page load gets a NEW conversation for this user.
    session_id = create_conversation(session["user_id"])
    session["session_id"] = session_id

    return render_template("index.html", username=session.get("username"))


@app.route("/api/new-chat", methods=["POST"])
@login_required
def new_chat():
    session_id = create_conversation(session["user_id"])
    session["session_id"] = session_id

    return jsonify({
        "success": True,
        "session_id": session_id,
    })


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(force=True)
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    session_id = session.get("session_id")

    if not session_id or not conversation_belongs_to_user(session_id, session["user_id"]):
        session_id = create_conversation(session["user_id"])
        session["session_id"] = session_id

    # ---- SAFETY LAYER: runs BEFORE any LLM call ----

    is_crisis, matched_category = check_for_crisis(user_message)

    save_message(
        session_id,
        "user",
        user_message,
        flagged=int(is_crisis),
    )

    if is_crisis:
        # Never let the LLM freestyle a response to acute crisis language.
        reply = CRISIS_RESPONSE

        save_message(
            session_id,
            "assistant",
            reply,
            flagged=1,
        )

        return jsonify({
            "reply": reply,
            "flagged": True,
            "category": matched_category,
        })

    # ---- Normal Gemini path ----

    history = get_history(session_id, limit=20)

    gemini_history = [
        types.Content(
            role="user" if role == "user" else "model",
            parts=[types.Part(text=content)],
        )
        for role, content, flagged, created_at in history[:-1]
    ]

    try:
        chat_session = client.chats.create(
            model=MODEL_NAME,
            config=chat_config,
            history=gemini_history,
        )

        response = chat_session.send_message(user_message)
        reply = response.text

    except Exception as exc:
        reply = (
            "I'm having trouble responding right now. "
            "If this is urgent, please reach out to a crisis line "
            "or someone you trust."
        )

        app.logger.error(
            "Gemini API error: %s",
            exc,
        )

    save_message(
        session_id,
        "assistant",
        reply,
        flagged=0,
    )

    return jsonify({
        "reply": reply,
        "flagged": False,
    })


@app.route("/api/history", methods=["GET"])
@login_required
def history():
    session_id = session.get("session_id")

    if not session_id or not conversation_belongs_to_user(session_id, session["user_id"]):
        return jsonify({
            "messages": []
        })

    rows = get_history(session_id)

    return jsonify({
        "messages": [
            {
                "role": role,
                "content": content,
                "flagged": bool(flagged),
                "created_at": created_at,
            }
            for role, content, flagged, created_at in rows
        ]
    })


@app.route("/api/conversations", methods=["GET"])
@login_required
def conversations():
    rows = get_conversations(session["user_id"])

    return jsonify({
        "conversations": [
            {
                "session_id": session_id,
                "title": title,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            for session_id, title, created_at, updated_at in rows
        ]
    })


@app.route("/api/conversations/<conversation_id>", methods=["GET"])
@login_required
def conversation(conversation_id):
    if not conversation_belongs_to_user(conversation_id, session["user_id"]):
        return jsonify({"error": "Conversation not found"}), 404

    rows = get_history(conversation_id)

    return jsonify({
        "session_id": conversation_id,
        "messages": [
            {
                "role": role,
                "content": content,
                "flagged": bool(flagged),
                "created_at": created_at,
            }
            for role, content, flagged, created_at in rows
        ]
    })


@app.route("/api/conversations/<conversation_id>", methods=["DELETE"])
@login_required
def delete_conversation_route(conversation_id):
    if not conversation_belongs_to_user(conversation_id, session["user_id"]):
        return jsonify({"error": "Conversation not found"}), 404

    delete_conversation(conversation_id, session["user_id"])

    # If the deleted conversation was the active one, start a fresh chat.
    if session.get("session_id") == conversation_id:
        session_id = create_conversation(session["user_id"])
        session["session_id"] = session_id
        return jsonify({"success": True, "new_session_id": session_id})

    return jsonify({"success": True, "new_session_id": None})


@app.route("/api/conversations/<conversation_id>/open", methods=["POST"])
@login_required
def open_conversation(conversation_id):
    if not conversation_belongs_to_user(conversation_id, session["user_id"]):
        return jsonify({
            "error": "Conversation not found"
        }), 404

    session["session_id"] = conversation_id

    return jsonify({
        "success": True,
        "session_id": conversation_id,
    })


if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000,
    )
