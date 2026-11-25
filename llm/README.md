# AI-Consolidated

Three related AI projects collected into one repository, with their shared code
extracted into a common [`shared/`](shared/) layer and **all real credentials
replaced by fake placeholders**. The projects are kept side-by-side and runnable;
`shared/` is a deduplicated reference library they can migrate onto.

```
AI-Consolidated/
├── .env.example          # shared secrets template (fake values) → copy to .env
├── .gitignore            # ignores .env, caches, model weights, media, data
├── shared/               # deduplicated common code (config, db, llm, email, netgsm)
└── projects/
    ├── tour-rag-agent/   # Qdrant-based RAG chatbot for tour/travel data
    ├── audio-to-text-ai/ # call-recording → Whisper → LLM analysis → DB/e-mail
    └── triage-notebooks/ # dataset building & model training for message triage
```

## Projects

### `projects/tour-rag-agent/`
A FastAPI social-chatbot / **RAG agent** over tour data stored in **Qdrant**.
Modular layout: `agents/`, `core/`, `qdrant/`, `search/` (filter & multi-vector
search), `prompts/`, `mcp/`, `models/`. Uses OpenAI for generation and a MySQL
`ayarlar` table for API keys and settings.

### `projects/audio-to-text-ai/`
A call-center pipeline: fetch call recordings from **Netgsm**, transcribe with
**faster-whisper**, analyze/summarize with **OpenAI / Gemini / Ollama**, store
results in **MySQL**, and send e-mail summaries over SMTP. Includes `Dockerfile`s,
a `mail/` summary job, a `socket/` Netgsm client, and the `enes/` experiment set.

### `projects/triage-notebooks/`
Jupyter notebooks that extract, clean and label customer messages to build a
**triage** training set (paired with `finetune_unsloth.py`). See its own README.

## Shared layer

See [`shared/README.md`](shared/README.md). It centralizes what the three
projects duplicated: env-based config, MySQL helpers, OpenAI/Gemini/Ollama client
factories, SMTP e-mail, and the Netgsm report client.

## Security — what was sanitized

All of the following **real** values were found in the original code and replaced
with fake placeholders in this copy:

- OpenAI API key (`sk-…`)
- MySQL hosts, users, database names and passwords (several sets)
- Netgsm usercode + password
- Yandex SMTP login + app password
- Qdrant server IP and an internal proxy host
- Company e-mail domain in recipient lists → `@example.com`
- Jupyter notebook **outputs were cleared** (they embedded customer messages/PII)

> ⚠️ **Rotate the real credentials.** Because they existed in the source (and some
> folders came from `-main` GitHub archives), treat the OpenAI key, DB passwords,
> Netgsm password and SMTP app password as **compromised** and regenerate them.

## Setup

```bash
# 1) install per-project deps
pip install -r projects/audio-to-text-ai/requirements.txt

# 2) configure secrets (never commit .env)
cp .env.example .env         # then edit .env with real values

# 3) optional infra
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant   # for tour-rag-agent
```

Each project also keeps its own README / notes (`tour-rag-agent/READ.me`,
`audio-to-text-ai/README.md`, `triage-notebooks/README.md`).
