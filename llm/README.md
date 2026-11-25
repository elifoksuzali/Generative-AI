# llm/ — workspace

This folder holds the three consolidated projects and the shared code they build
on. For the high-level overview see the [repository root README](../README.md).

```
llm/
├── .env.example     # shared secrets template (fake values) → copy to .env
├── .gitignore       # ignores .env, caches, model weights, media, data
├── shared/          # deduplicated common code — see shared/README.md
└── projects/
    ├── tour-rag-agent/     # RAG chatbot (FastAPI + Qdrant + OpenAI)
    ├── audio-to-text-ai/   # Whisper + LLM call-analysis pipeline
    └── triage-notebooks/   # dataset building & model training
```

## Projects

- [**tour-rag-agent**](projects/tour-rag-agent/README.md) — multi-agent travel
  chatbot with triple Qdrant retrieval and per-chat memory.
- [**audio-to-text-ai**](projects/audio-to-text-ai/README.md) — Netgsm → Whisper
  → LLM analysis → MySQL → e-mail summary pipeline.
- [**triage-notebooks**](projects/triage-notebooks/README.md) — extract/clean/label
  customer messages to train a triage model.

## Shared layer

[`shared/`](shared/README.md) centralizes env-based config, MySQL helpers,
OpenAI/Gemini/Ollama client factories, SMTP e-mail and the Netgsm client, so the
projects stop duplicating that plumbing (and stop hardcoding secrets).

## Setup

```bash
cp .env.example .env     # fill in real values locally; never commit .env
pip install -r projects/audio-to-text-ai/requirements.txt
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant   # for tour-rag-agent
```

## Security

All real credentials were replaced with fake placeholders, notebook outputs were
cleared, and employee names were anonymized. **Rotate the original OpenAI key, DB
passwords, Netgsm password and SMTP app password** — they must be considered
compromised. See the [root README](../README.md#security) for the full list.
