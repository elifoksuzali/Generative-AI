# shared/

Deduplicated building blocks that the three projects previously re-implemented
(often with hardcoded credentials). Everything here reads secrets from the
environment via [`config.py`](config.py) — nothing is hardcoded.

| Module | Purpose | Replaces (originals) |
|--------|---------|----------------------|
| `config.py` | Env-based settings (DB, Qdrant, OpenAI, Gemini, Ollama, SMTP, Netgsm) | scattered `os.getenv` + inline dicts |
| `db.py` | MySQL connection + `ayarlar` key/value lookups | `audio-to-text-ai/database/db.py`, `tour-rag-agent/api.py` `DB_CONFIG` |
| `llm.py` | OpenAI / Gemini / Ollama client factories | inline `OpenAI(api_key=...)`, `genai.configure(...)` in every script |
| `email_utils.py` | SMTP send helper (STARTTLS) | copy-pasted SMTP block in `3wh.py`, `test-api.py`, `whisper.py`, `mail/mail.py` |
| `netgsm.py` | Netgsm `netsantral/report` client | repeated Netgsm request in the audio scripts |

## Usage

```python
from shared import config, db, llm, email_utils, netgsm

client = llm.openai_client()                 # key from OPENAI_API_KEY
conn = db.create_connection()                # creds from env
email_utils.send_email("Subject", "Body", ["someone@example.com"])
```

> This is a **reference layer**. The projects under `../projects/` still run with
> their own original code; migrate them to import from `shared` incrementally.

## Setup

```bash
pip install python-dotenv openai google-generativeai mysql-connector-python requests
cp ../.env.example ../.env     # then fill in real values (never commit .env)
```
