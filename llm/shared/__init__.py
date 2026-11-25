"""Shared, deduplicated building blocks for the consolidated AI projects.

Modules:
    config       env-based settings (DB, Qdrant, OpenAI, Gemini, Ollama, SMTP, Netgsm)
    db           MySQL connection + `ayarlar` settings/key lookups
    llm          OpenAI / Gemini / Ollama client factories
    email_utils  SMTP send helper
    netgsm       Netgsm call-report API client
"""
