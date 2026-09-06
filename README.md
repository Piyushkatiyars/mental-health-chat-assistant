# AI-Powered Mental Health Chat Assistant

A Flask + Gemini API chat assistant with a rule-based crisis-safety layer.
Built as a portfolio project — **not a clinical tool**.

## 🚀 Live Demo

👉 **Try the AI Mental Health Chat Assistant:**
https://mental-health-chat-assistant.onrender.com

> ⚠️ **Disclaimer:** This AI assistant is for general emotional support and informational purposes only. It is not a substitute for professional mental health care.

## Why this project stands out

Most student AI/ML portfolios have an MNIST classifier or movie recommender.

This project instead demonstrates:

* LLM integration with a real API (Gemini) and conversation memory
* **Responsible AI design:** a deterministic safety layer that intercepts crisis language *before* it reaches the LLM
* Clear system-prompt engineering with explicit behavioral boundaries
* SQLite-based conversation persistence
* Flask backend with a simple web-based chat interface

## Setup

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-api-key-here"
export FLASK_SECRET_KEY="something-random"
python app.py
```

Visit:

```text
http://localhost:5000
```

## Architecture

```text
User message
     |
     v
[safety.py: check_for_crisis()]
     |
     |--- crisis pattern matched ---> Fixed crisis-resource response
     |                                (LLM is never called)
     |
     |--- no match -----------------> Gemini API call
                                      |
                                      v
                              System prompt +
                              conversation history
                                      |
                                      v
                              Response saved to
                              SQLite + shown to user
```

## Files

* `app.py` — Flask routes, session handling, SQLite persistence
* `safety.py` — rule-based crisis-keyword detection
* `prompts.py` — system prompt defining the assistant's boundaries
* `templates/index.html` — chat interface
* `static/` — frontend assets

## Key Interview Talking Points

* The safety layer is **rule-based** because this specific check needs auditability and predictable behavior.
* Crisis-related messages can be intercepted **before the LLM is called**.
* The application is intentionally scoped to general emotional support and psychoeducation.
* It is **not a diagnostic, treatment, or medical-advice tool**.
* Conversation history is maintained using SQLite.

## Technologies Used

* **Python**
* **Flask**
* **Google Gemini API**
* **SQLite**
* **HTML / CSS / JavaScript**
* **REST API**
* **Prompt Engineering**
* **Responsible AI / Safety Guardrails**

## Future Improvements

* Add authentication for multi-user support
* Add a "mood check-in" feature using simple non-clinical tags
* Add rate limiting to the `/api/chat` endpoint
* Improve crisis-resource localization
* Add automated testing for the safety layer
* Improve conversation-memory management

## Disclaimer

This project is created for educational and portfolio purposes. It is not intended to diagnose, treat, or provide medical advice for mental health conditions. Users experiencing an emergency should contact appropriate local emergency or crisis-support services.
