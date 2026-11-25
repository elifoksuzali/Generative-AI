"""Shared LLM client factories for OpenAI, Google Gemini and Ollama.

All three projects created these clients inline (often with hardcoded keys).
This module centralizes them and sources keys from `shared.config`.
"""
from __future__ import annotations

from . import config


def openai_client(api_key: str | None = None):
    """Return an OpenAI client. Falls back to OPENAI_API_KEY from env."""
    from openai import OpenAI
    return OpenAI(api_key=api_key or config.OPENAI_API_KEY)


def ollama_client(host: str | None = None, api_key: str | None = None):
    """Return an OpenAI-compatible client pointed at a local Ollama server."""
    from openai import OpenAI
    host = host or config.OLLAMA_HOST
    return OpenAI(
        api_key=api_key or config.OLLAMA_API_KEY,
        base_url=f"http://{host}:11434/v1",
    )


def gemini_model(model_name: str = "gemini-1.5-flash", api_key: str | None = None):
    """Configure google-generativeai and return a GenerativeModel."""
    import google.generativeai as genai
    genai.configure(api_key=api_key or config.GEMINI_API_KEY)
    return genai.GenerativeModel(model_name)
