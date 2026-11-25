# tour-rag-agent

A **FastAPI** chatbot that answers travel/tour questions using
**Retrieval-Augmented Generation (RAG)** over a **Qdrant** vector database and
**OpenAI** models. It is built as a small **multi-agent** system with per-chat
memory, and is designed to be plugged into a social/messaging backend: it receives
a structured request (customer, chat history, last message, prompt settings) and
returns a structured reply.

## How it works

```
         incoming SocialRequest (customer, chatId, previousMessages, lastMessage, aiSettings)
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │   handle_social_message  │  (core/logic.py)
                      └─────────────────────────┘
                                   │
         ┌─────────────────────────┼───────────────────────────┐
         ▼                         ▼                           ▼
  Question Analyzer         Query Router                 Reply Agent
   (classify intent:     (detail / list / more)     (compose final answer)
   tour_info/list/…)                                        │
         │                                                   │
         ▼                                                   ▼
   triple Qdrant search ──► filter + semantic + multivector  Response Validator
   (qdrant/, search/)       → merge & dedup results          (sanity-check reply)
         │
         ▼
   per-chat ConversationContext (shown IDs, filters, last tours)
         │
         ▼
   optional tour-price lookup via MCP (mcp/mcp.py) → SocialResponse
```

1. **Intent analysis** — the *question analyzer* agent classifies the message
   (`tour_info`, `tour_list`, detail field, category, …).
2. **Retrieval** — for tour queries, three Qdrant searches run and are merged:
   - **Filter search** — field-based filtering (`search/filter_search.py`)
   - **Semantic search** — dense-vector similarity
   - **Multivector search** — dense + sparse vectors (`search/multivector_search.py`)
3. **Context tracking** — a `ConversationContext` per `chatId` remembers which
   tours were already shown and the active filters (type, category, transport,
   accommodation, night count), so "show me more" returns *new* results.
4. **Answer generation** — the *reply* agent composes the response; the
   *response validator* agent checks it. Prompts come from the request's
   `aiSettings` via `global_prompt_manager`.
5. **Price lookup** — `mcp/mcp.py` (`fetch_tour_price`) fetches live tour prices.

## Project structure

| Path | Role |
|------|------|
| `api.py` | FastAPI app, CORS, IP allow-list middleware, request entry point |
| `core/logic.py` | `handle_social_message` orchestration |
| `core/context.py` | `ConversationContext` (per-chat memory) |
| `agents/agent.py`, `agents/simpleAgent.py` | agent manager + agent definitions |
| `main/main.py` | retrieval, intent context, tour-ID resolution helpers |
| `qdrant/qdrantDb.py` | Qdrant client + collection access |
| `qdrant/context.py`, `qdrant/display_result.py` | retrieval glue & formatting |
| `search/filter_search.py`, `search/multivector_search.py` | search strategies |
| `models/schema.py` | Pydantic models (`SocialRequest`, `SocialResponse`, …) |
| `prompts/global_prompt_manager.py`, `prompts/handle_db.py` | prompt loading |
| `db_key/db.py` | `KeyManager` — loads API keys from the DB `ayarlar` table |
| `mcp/mcp.py` | tour-price lookup (MCP-style tool) |
| `update/updateDb.py`, `value/value.py` | data update + in-memory tour cache |
| `qdrant_search.py` | standalone Qdrant search script |
| `config.py` | env-based settings (`DB_*`, `URL_LINK` for Qdrant) |

## Requirements

- Python 3.10+
- A running **Qdrant** instance (default `URL_LINK=http://localhost:6333`)
- A **MySQL** database exposing an `ayarlar` (settings) table that holds API keys
- An **OpenAI** API key (used via `gpt-4o-mini`)

```bash
pip install fastapi uvicorn openai qdrant-client pydantic mysql-connector-python python-dotenv
```

## Configuration

Secrets are read from the environment (see the repo-root `llm/.env.example`):

```env
DB_HOST=...        # MySQL host that stores settings/keys
DB_USER=...
DB_PASSWORD=...
DB_NAME=...
URL_LINK=http://localhost:6333   # Qdrant endpoint
```

API keys (OpenAI, Qdrant) are loaded at runtime from the DB `ayarlar` table via
`KeyManager`, not hardcoded.

## Running

```bash
# start Qdrant (if not already running)
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# run the API
uvicorn api:app --host 0.0.0.0 --port 8000
```

Then POST a `SocialRequest` payload to the chat endpoint (see `models/schema.py`
for the exact shape: `customer`, `chatId`, `previousMessages`, `lastMessage`,
`aiSettings.prompts`).

## Notes

- Prompts are supplied per request through `aiSettings`, so behavior can be tuned
  without code changes.
- Credentials in this copy are placeholders — set real values via `.env` / the DB.
