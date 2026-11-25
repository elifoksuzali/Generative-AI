# Generative-AI

A monorepo of three related **Generative-AI / LLM** projects, collected under
[`llm/`](llm/) with their shared building blocks factored into a common
[`llm/shared/`](llm/shared/) layer. All real credentials have been replaced with
fake placeholders and notebook outputs cleared, so the repository is safe to share.

- **tour-rag-agent** — a FastAPI chatbot that answers travel questions using
  Retrieval-Augmented Generation over a Qdrant vector database.
- **audio-to-text-ai** — a call-center pipeline that transcribes call recordings
  with Whisper and summarizes/analyzes them with an LLM.
- **triage-notebooks** — notebooks that build and label a dataset for a customer
  message **triage** model (fine-tuned with Unsloth).

---

## Repository layout

```
Generative-AI/
├── README.md                     ← you are here (general overview)
└── llm/
    ├── README.md                 ← workspace overview
    ├── .env.example              ← shared secrets template (fake values)
    ├── .gitignore                ← ignores .env, caches, weights, media, data
    ├── shared/                   ← deduplicated common code
    │   ├── config.py             ← env-based settings (DB, Qdrant, OpenAI, …)
    │   ├── db.py                 ← MySQL connection + `ayarlar` key/value lookups
    │   ├── llm.py                ← OpenAI / Gemini / Ollama client factories
    │   ├── email_utils.py        ← SMTP e-mail helper
    │   └── netgsm.py             ← Netgsm call-report API client
    └── projects/
        ├── tour-rag-agent/       ← RAG chatbot (FastAPI + Qdrant + OpenAI)
        ├── audio-to-text-ai/     ← Whisper + LLM call-analysis pipeline
        └── triage-notebooks/     ← dataset building & model training
```

Each project has its own detailed `README.md` — follow the links below.

## Projects at a glance

| Project | What it does | Core tech |
|---------|--------------|-----------|
| [tour-rag-agent](llm/projects/tour-rag-agent/README.md) | Multi-agent travel chatbot; triple Qdrant search (filter + semantic + multivector), per-chat memory, tour-price lookup | FastAPI, OpenAI GPT-4o-mini, Qdrant, Pydantic, MySQL |
| [audio-to-text-ai](llm/projects/audio-to-text-ai/README.md) | Pull call recordings from Netgsm → transcribe (Whisper) → analyze/summarize (LLM) → store in MySQL → e-mail summary | faster-whisper, OpenAI/Gemini/Ollama, PyMySQL, Docker |
| [triage-notebooks](llm/projects/triage-notebooks/README.md) | Extract/clean/label customer messages and build a triage training set | Jupyter, pandas, MySQL, Unsloth/Transformers |

## The shared layer

The three projects independently re-implemented the same plumbing (DB
connections, LLM clients, SMTP, Netgsm), often with hardcoded secrets.
[`llm/shared/`](llm/shared/README.md) centralizes all of it and reads every
secret from the environment. New code should import from `shared`; the existing
projects keep their original code and can migrate incrementally.

## Quick start

```bash
# 1) clone
git clone https://github.com/elifoksuzali/Generative-AI.git
cd Generative-AI/llm

# 2) configure secrets (never commit the real .env)
cp .env.example .env            # then fill in real values

# 3) install the deps for the project you want, e.g.
pip install -r projects/audio-to-text-ai/requirements.txt

# 4) optional infra for the RAG agent
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```
