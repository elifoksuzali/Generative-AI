# audio-to-text-ai

A **call-center automation pipeline** that turns phone-call recordings into
searchable, summarized, analyzed text. It pulls call records from **Netgsm**,
downloads the audio, transcribes it with **Whisper**, analyzes and summarizes the
conversation with an **LLM** (OpenAI / Gemini / Ollama), stores the results in
**MySQL**, and sends e-mail summaries to the team.

## Pipeline

```
Netgsm call report (date range)
        │   (socket/ + netgsm API)
        ▼
download each call recording (audio)
        │
        ▼
transcribe with faster-whisper  ──►  raw transcript (+ optional speaker split)
        │
        ▼
analyze & summarize with LLM  ──►  summary, topics, action items, cost tracking
   (OpenAI / Gemini / Ollama)
        │
        ├──►  save to MySQL (cagritakip / cagritakip_santral tables)
        └──►  e-mail daily summary via SMTP (mail/)
```

## Project structure

| Path | Role |
|------|------|
| `whisper.py` | main end-to-end pipeline (download → transcribe → analyze → store) |
| `3wh.py` | earlier/alternate full pipeline variant |
| `test-api.py` | API/pipeline testing script |
| `gemini.py` | Gemini-based analysis variant |
| `ollama_func.py` | Ollama (local LLM) helper functions |
| `database/db.py` | MySQL connection + settings/keys/prompts + call-record inserts |
| `mail/mail.py` | compose & send summary e-mails (OpenAI) |
| `mail/ollama_mail.py` | same, using a local Ollama model |
| `socket/socket_netgsm.py` | low-level Netgsm socket client |
| `a.py` | Netgsm statistics request snippet |
| `enes/` | experiment set (Flask services, alternate Dockerfiles) |
| `test.html` | simple test front-end |
| `requirements.txt`, `Dockerfile` | dependencies & container image |

## Data model (MySQL)

- `ayarlar` — key/value settings table; holds API keys (`gpt_api_key`,
  `gemini_api_key`, `ollama_api_key`), the base URL, and the last-processed
  timestamp (`cagriaisonkontrol`).
- `cagritakip_santral` — raw call records (id, date, caller, callee, direction,
  duration).
- `cagritakip` — enriched records with transcript, summary and GPT cost.
- `kurum_ai_prompt` — the prompt templates (`summary_gpt_prompt`,
  `speaker_gpt_prompt`, `mail_prompt`, `gemini_mail_prompt`).

## Requirements

See `requirements.txt`:

```
mysql-connector-python  openai  requests  faster-whisper
audiosegment  google-generativeai  python-dotenv  numpy  torch
```

Whisper benefits from a CUDA GPU (`requirements-gpu.txt` / `Dockerfile.gpu`
variants exist in the broader project), but runs on CPU too.

## Configuration

All secrets come from the environment (see the repo-root `llm/.env.example`):

```env
DB_HOST=...  DB_USER=...  DB_PASSWORD=...  DB_NAME=...
NETGSM_USERCODE=...  NETGSM_PASSWORD=...
SMTP_HOST=smtp.yandex.com  SMTP_LOGIN=...  SMTP_PASSWORD=...
# LLM keys are read from the MySQL `ayarlar` table at runtime
```

## Running

```bash
pip install -r requirements.txt

# with Docker
docker build -t audio-to-text-ai .
docker run --env-file ../../.env audio-to-text-ai

# or directly
python whisper.py
```

## Notes

- Credentials, the Netgsm usercode/password, the SMTP app password and recipient
  e-mail addresses in this copy are **placeholders** — provide real ones via `.env`
  and the DB.
- LLM usage cost is tracked per call (input/output/cached tokens) for GPT-4o-mini.
