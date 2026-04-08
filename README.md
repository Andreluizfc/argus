# Argus

Local multi-agent system powered by [Agno](https://github.com/agno-agi/agno), [Ollama](https://ollama.com), and [Langfuse](https://langfuse.com). Runs entirely on your machine — no cloud APIs, no data leaves your laptop.

A **team leader** agent coordinates two specialized sub-agents (Researcher + Writer) to research topics and produce written content, all using tiny language models via local inference. Every request is traced to Langfuse for full observability.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Docker Compose                           │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌────────────────────────────┐    │
│  │ frontend │──▶│ agno-app │──▶│       Langfuse v3          │    │
│  │  :3000   │   │  :8000   │   │        :4000               │    │
│  │React Chat│SSE│          │   │  postgres + clickhouse     │    │
│  └──────────┘   │  Leader  │   │  redis + minio             │    │
│                 │  ┌──┴──┐ │   └────────────────────────────┘    │
│                 │  R     W │                                     │
│                 └────┬─────┘                                     │
│                      │                                           │
└──────────────────────┼───────────────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │     Ollama      │
              │  (native macOS) │
              │  Metal GPU accel│
              └─────────────────┘
```

| Component | Where | Port |
|-----------|-------|------|
| Ollama | Native macOS (Metal GPU) | 11434 |
| Backend (Agno + FastAPI) | Docker | 8000 |
| Frontend (React + Vite) | Docker | 3000 |
| Langfuse (observability) | Docker | 4000 |

## Models

| Role | Model | Size | Agent Score |
|------|-------|------|-------------|
| Team Leader | `qwen3:1.7b` | 1.4 GB | 0.960 |
| Researcher | `qwen3:0.6b` | 522 MB | 0.880 |
| Writer | `qwen3:0.6b` | 522 MB | 0.880 |

Total disk: ~2.4 GB. Peak RAM: ~3 GB. Response time: ~5s per request.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com) installed natively (`brew install ollama`)

## Quick Start

**1. Start Ollama and pull models:**

```bash
brew services start ollama
ollama pull qwen3:1.7b
ollama pull qwen3:0.6b
```

**2. Clone and run:**

```bash
git clone git@github.com:Andreluizfc/argus.git
cd argus
docker compose up -d
```

First startup takes ~2 minutes (Langfuse runs database migrations).

**3. Open:**

| Service | URL |
|---------|-----|
| Chat UI | [http://localhost:3000](http://localhost:3000) |
| Langfuse Dashboard | [http://localhost:4000](http://localhost:4000) |
| API Docs | [http://localhost:8000/agents](http://localhost:8000/agents) |

**Langfuse login:** `admin@argus.local` / `argus-admin`

## Chat Features

- Streaming responses with real-time token rendering
- Markdown formatting (headings, bold, lists, tables, links)
- Syntax-highlighted code blocks with copy button
- LaTeX math formula rendering (inline `$...$` and block `$$...$$`)
- Tool call visibility (see when agents delegate and invoke tools)
- Conversation continuity via session persistence
- Dark theme UI (Claude/ChatGPT-style layout)

## Observability (Langfuse)

Every agent request is automatically traced to Langfuse at `localhost:4000`.

**What's tracked:**

| Metric | Description |
|--------|-------------|
| Latency | End-to-end duration per request (ms) |
| Status | HTTP status code |
| Component | Which team/agent handled the request |
| Path | API endpoint called |
| User feedback | Thumbs up/down via `POST /feedback` |

**Langfuse stack** (all in Docker Compose):
- `langfuse-web` — Dashboard + API (port 4000)
- `langfuse-worker` — Async event processing
- `langfuse-postgres` — Transactional DB
- `langfuse-clickhouse` — Analytics OLAP
- `langfuse-redis` — Queue + cache
- `langfuse-minio` — S3-compatible blob storage

Project and API keys are auto-provisioned on first boot — no manual setup.

## Project Structure

```
argus/
├── docker-compose.yml          # All services (app + langfuse)
├── Dockerfile                  # Python backend image
├── pyproject.toml              # Python dependencies
├── src/argus/
│   ├── app.py                  # AgentOS entrypoint + Langfuse middleware
│   ├── config.py               # Settings (pydantic-settings)
│   ├── models.py               # Ollama model factories
│   ├── tracing.py              # Langfuse REST trace ingestion
│   ├── feedback.py             # POST /feedback endpoint
│   ├── tools/                  # Agent tools (research, writing)
│   ├── agents/                 # Agent definitions (researcher, writer)
│   └── teams/                  # Team orchestration (content team)
├── frontend/
│   ├── Dockerfile              # Node frontend image
│   ├── src/
│   │   ├── api/agno.ts         # SSE streaming client
│   │   ├── hooks/useChat.ts    # Chat state management
│   │   └── components/         # React UI components
└── tests/                      # pytest test suite
```

## Configuration

All settings via environment variables (prefix `ARGUS_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ARGUS_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `ARGUS_LEADER_MODEL` | `qwen3:1.7b` | Team leader model |
| `ARGUS_RESEARCHER_MODEL` | `qwen3:0.6b` | Researcher agent model |
| `ARGUS_WRITER_MODEL` | `qwen3:0.6b` | Writer agent model |
| `ARGUS_DATABASE_PATH` | `data/agno.db` | SQLite session storage |
| `ARGUS_LANGFUSE_ENABLED` | `true` | Enable/disable Langfuse tracing |
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-argus-local` | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | `sk-lf-argus-local` | Langfuse project secret key |
| `LANGFUSE_BASE_URL` | `http://langfuse-web:3000` | Langfuse server URL |

## API

```bash
# List agents
curl http://localhost:8000/agents

# List teams
curl http://localhost:8000/teams

# Run team (streaming)
curl -N -X POST http://localhost:8000/teams/content-team/runs \
  -F "message=Write about Python decorators" \
  -F "stream=true"

# Run team (non-streaming)
curl -X POST http://localhost:8000/teams/content-team/runs \
  -F "message=Say hello" \
  -F "stream=false"

# Submit feedback
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "abc-123", "score": 1, "comment": "Great response"}'
```

## Development

**Run backend locally (without Docker):**

```bash
uv sync
uv run uvicorn argus.app:app --reload --port 8000
```

**Run frontend locally:**

```bash
cd frontend
npm install
npm run dev
```

**Run tests:**

```bash
uv run pytest tests/ -v
```

**Lint:**

```bash
uvx ruff check src/ tests/
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | [Agno](https://github.com/agno-agi/agno) (AgentOS) |
| LLM inference | [Ollama](https://ollama.com) (Metal GPU) |
| Observability | [Langfuse](https://langfuse.com) v3 (self-hosted) |
| Backend | Python 3.13, FastAPI, pydantic-settings |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4 |
| Markdown | react-markdown, remark-gfm |
| Math | KaTeX (remark-math + rehype-katex) |
| Code highlighting | react-syntax-highlighter (oneDark) |
| Persistence | SQLite |
| Containerization | Docker Compose |

## License

MIT
