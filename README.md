# AI-Powered Mental Health Chat Assistant

A Flask + Gemini API chat assistant with a rule-based crisis-safety layer.
Built as a portfolio project — **not a clinical tool**.

## Why this project stands out

Most student AI/ML portfolios have an MNIST classifier or movie recommender.
This project instead demonstrates:
- LLM integration with a real API (Gemini) and conversation memory
- **Responsible AI design**: a deterministic safety layer that intercepts
  crisis language *before* it reaches the LLM, rather than trusting the
  model to handle high-stakes situations on its own
- Clear system-prompt engineering with explicit behavioral boundaries

## Setup

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-api-key-here"
export FLASK_SECRET_KEY="something-random"
python app.py
```

Visit `http://localhost:5000`.

## Architecture

```
User message
     |
     v
[safety.py: check_for_crisis()]  --- if crisis pattern matched --->  Fixed crisis-resource response
     |                                                                  (LLM is never called)
     | (no match)
     v
[Gemini API call with system prompt + conversation history]
     |
     v
Response saved to SQLite + shown to user
```

## Files
- `app.py` — Flask routes, session handling, SQLite persistence
- `safety.py` — rule-based crisis-keyword detection (the key differentiator)
- `prompts.py` — system prompt defining the assistant's boundaries
- `templates/index.html`, `static/` — minimal chat UI

## Important notes for your demo/interview talking points
- Explain **why** the safety layer is rule-based, not ML-based, for this
  specific check: auditability and predictability matter more than nuance
  when the cost of a missed detection is high.
- Mention this is not a diagnostic or treatment tool — it's scoped to
  general support and psychoeducation only.
- Crisis helpline numbers are placeholders — swap in ones appropriate for
- The Gemini model name in `app.py` (currently `gemini-3.6-flash`) may need

## Next steps to extend
- Add authentication for multi-user support
- Add a "mood check-in" feature (simple tags, not clinical scoring)
- Deploy to Render/Replit and record a demo video (like your No-Show Guard project)
- Add basic rate limiting to the `/api/chat` endpoint
