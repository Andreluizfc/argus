# Argus

Local multi-agent system powered by [Agno](https://github.com/agno-agi/agno) and [Ollama](https://ollama.com). Runs entirely on your machine — no cloud APIs, no data leaves your laptop.

A **team leader** agent coordinates two specialized sub-agents (Researcher + Writer) to research topics and produce written content, all using tiny language models via local inference.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Docker Compose                     │
│                                                         │
│  ┌──────────────┐     ┌─────────────────────────────┐   │
│  │   frontend   │     │         agno-app            │   │
│  │   :3000      │────▶│          :8000              │   │
│  │  React Chat  │ SSE │                             │   │
│  └──────────────┘     │   Team Leader (qwen3:1.7b)  │   │
│                       │        ┌──────┴──────┐      │   │
│                       │   Researcher     Writer     │   │
│                       │   (qwen3:0.6b)  (qwen3:0.6b)│   │
│                       └──────────────┬──────────────┘   │
│                                      │                  │
└──────────────────────────────────────┼──────────────────┘
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

**3. Open the chat:**

[http://localhost:3000](http://localhost:3000)

## Chat Features

- Streaming responses with real-time token rendering
- Markdown formatting (headings, bold, lists, tables, links)
- Syntax-highlighted code blocks with copy button
- LaTeX math formula rendering (inline `$...$` and block `$$...$$`)
- Tool call visibility (see when agents delegate and invoke tools)
- Conversation continuity via session persistence
- Dark theme UI

## Project Structure

```
argus/
├── docker-compose.yml          # Backend + frontend services
├── Dockerfile                  # Python backend image
├── pyproject.toml              # Python dependencies
├── src/argus/
│   ├── app.py                  # AgentOS FastAPI entrypoint
│   ├── config.py               # Settings (pydantic-settings)
│   ├── models.py               # Ollama model factories
│   ├── tools/                  # Agent tools (research, writing)
│   ├── agents/                 # Agent definitions (researcher, writer)
│   └── teams/                  # Team orchestration (content team)
├── frontend/
│   ├── Dockerfile              # Node frontend image
│   ├── src/
│   │   ├── api/agno.ts         # SSE streaming client
│   │   ├── hooks/useChat.ts    # Chat state management
│   │   └── components/         # React UI components
├── tests/                      # pytest test suite
└── docs/plans/                 # Implementation plan
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

## API

The backend exposes AgentOS endpoints:

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
| Backend | Python 3.13, FastAPI, pydantic-settings |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4 |
| Markdown | react-markdown, remark-gfm |
| Math | KaTeX (remark-math + rehype-katex) |
| Code highlighting | react-syntax-highlighter (oneDark) |
| Persistence | SQLite |
| Containerization | Docker Compose |

## License

MIT
