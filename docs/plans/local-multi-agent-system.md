# Local Multi-Agent System with Agno + Ollama

> **Date:** 2026-04-07
> **Status:** In Progress
> **Depends on:** None

## Goal

Build a fully local multi-agent system from scratch using **Agno** (orchestration), **Ollama** (local LLM inference), a **React chat UI** (conversation interface), and **Docker Compose** (microservices) — running on a MacBook with 16GB RAM, zero external API dependencies.

---

## 1. Architecture

### System Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Docker Compose                              │
│                                                                      │
│  ┌──────────────┐                                                    │
│  │   frontend   │  React Chat UI (Vite + React 19)                   │
│  │   :3000      │  ─────────────── SSE Stream ──────────┐            │
│  └──────────────┘                                       │            │
│                                                         ▼            │
│  ┌───────────────┐    ┌──────────────────────────────────────────┐   │
│  │               │    │              agno-app :8000              │   │
│  │    ollama     │◄───│                                          │   │
│  │    :11434     │    │  ┌──────────────────────────────────┐    │   │
│  │               │    │  │         Team Leader              │    │   │
│  │  Models:      │    │  │        (Coordinate mode)         │    │   │
│  │  - qwen3:1.7b │    │  │              │                   │    │   │
│  │  - qwen3:0.6b │    │  │       ┌──────┴──────┐            │    │   │
│  │               │    │  │       │             │            │    │   │
│  │               │    │  │    Agent 1       Agent 2         │    │   │
│  │               │    │  │   Researcher     Writer          │    │   │
│  │               │    │  └──────────────────────────────────┘    │   │
│  └───────────────┘    │                                          │   │
│         ▲             │  ┌──────────────────────────────────┐    │   │
│         │             │  │  AgentOS (FastAPI)               │    │   │
│         │             │  │  POST /teams/{id}/runs (SSE)     │    │   │
│         │             │  │  GET  /agents                    │    │   │
│         │             │  │  GET  /sessions                  │    │   │
│         │             │  └──────────────────────────────────┘    │   │
│         │             └──────────────────────────────────────────┘   │
│         │                              │                             │
│  ┌──────┴────────┐       ┌─────────────┴────────────────────┐        │
│  │  ollama-pull  │       │         sqlite-data              │        │
│  │ (init models) │       │    (volume: ./data/agno.db)      │        │
│  └───────────────┘       └──────────────────────────────────┘        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Microservices

| Service | Image | Purpose | Port |
|---------|-------|---------|------|
| `ollama` | `ollama/ollama:latest` | Local LLM inference server | 11434 |
| `ollama-pull` | `ollama/ollama:latest` | Init container — pulls models on first run | — |
| `agno-app` | Custom `Dockerfile` | Agno agents + AgentOS FastAPI runtime | 8000 |
| `frontend` | Custom `frontend/Dockerfile` | React chat UI (Vite dev server) | 3000 |

### Model Selection

Based on verified benchmarks ([MikeVeerman's tool-calling benchmark](https://github.com/MikeVeerman/tool-calling-benchmark)), Ollama docs, Agno docs, and GitHub issues — prioritizing the **smallest models with reliable tool calling**:

| Role | Model | Ollama Tag | Disk | RAM | Agent Score | Why |
|------|-------|------------|------|-----|-------------|-----|
| **Team Leader** | Qwen3 1.7B | `qwen3:1.7b` | 1.4 GB | ~2-3 GB | **0.960** | Best sub-4B model. Perfect restraint (1.0), high action accuracy (0.9). Only model to get all hard prompts right |
| **Sub-Agent 1** (Researcher) | Qwen3 0.6B | `qwen3:0.6b` | 523 MB | ~1-1.5 GB | **0.880** | Smallest viable model with native Ollama tool support. Perfect restraint, acceptable action score |
| **Sub-Agent 2** (Writer) | Qwen3 0.6B | `qwen3:0.6b` | 523 MB | ~1-1.5 GB | **0.880** | Same model — writer needs less reasoning than researcher. Keeps total footprint minimal |

**Total model footprint**: ~2.4 GB on disk, ~2-3 GB RAM at inference (only one model loaded at a time).

**Ultra-lightweight alternative**: Use `qwen3:0.6b` for ALL agents including leader. Total: 523 MB disk, ~1.5 GB RAM. Trades leader reasoning quality for even smaller footprint.

**Speed alternative**: Replace `qwen3:0.6b` sub-agents with `lfm2.5-thinking:1.2b` (Liquid AI, 900 MB, 0.920 agent score, 7x faster inference — non-transformer state-space model). Best speed/quality ratio for sub-4B.

Ollama swaps models in/out on demand. Since all agents share `qwen3:0.6b`, only the leader swap (0.6B → 1.7B → 0.6B) incurs load time.

### Benchmark Context (Verified)

| Model | Params | Agent Score | Latency | Notes |
|-------|--------|-------------|---------|-------|
| **qwen3:1.7b** | 1.7B | 0.960 | 10.6s | Top pick — all hard prompts correct |
| **lfm2.5-thinking:1.2b** | 1.2B | 0.920 | 1.5s | 7x faster, non-transformer |
| **qwen3:0.6b** | 0.6B | 0.880 | 3.4s | Smallest viable for tool calling |
| qwen2.5:1.5b | 1.5B | 0.800 | 2.2s | Older gen, outclassed by qwen3 |
| gemma3:1b | 1B | 0.690 | 2.3s | Mediocre tool calling |
| llama3.2:3b | 3B | — | — | Unreliable format, not recommended |

### Known Caveats

- `tool_choice` parameter is **not supported** by Ollama — the model decides when to call tools
- Avoid **Qwen3.5** for tool calling — known Ollama template bug (issue #14493, XML/JSON format mismatch)
- Qwen3 may hallucinate tool calls with wrong arguments (issue #11135) — worse at smaller sizes. Mitigate with simple tool schemas and clear docstrings
- Agno tool call parsing was fixed in **v1.1.13** — use latest version
- Keep tools per agent at 2-3 (not 5+) for sub-2B models — smaller context helps accuracy

### AgentOS API Contract

The frontend communicates with AgentOS via these endpoints:

| Endpoint | Method | Purpose | Format |
|----------|--------|---------|--------|
| `/agents` | GET | List available agents | JSON |
| `/teams` | GET | List available teams | JSON |
| `/teams/{id}/runs` | POST | Execute team run | **Multipart form data** → SSE stream |
| `/agents/{id}/runs` | POST | Execute agent run | **Multipart form data** → SSE stream |
| `/sessions` | GET | List conversation sessions | JSON |
| `/sessions/{id}` | GET | Get session with history | JSON |
| `/sessions/{id}` | DELETE | Delete a session | JSON |

**Critical**: Run endpoints accept **multipart form data** (not JSON). Key fields: `message` (str), `stream` (bool, default `true`), `session_id` (optional str — pass to continue conversation).

**SSE Event Types** (streamed response):

| Event | Purpose |
|-------|---------|
| `RunStarted` | Run initiated with run_id, session_id |
| `RunContent` | Incremental text chunk |
| `ToolCallStarted` | Agent invoked a tool (name + args) |
| `ToolCallCompleted` | Tool returned result |
| `ReasoningStep` | Chain-of-thought step |
| `RunCompleted` | Final response with full content + metrics |
| `RunError` | Error occurred |

**CORS**: AgentOS allows `http://localhost:3000` by default — no extra config needed.

### Expected Outcomes

| Metric | Cloud APIs | This System |
|--------|------------|-------------|
| Cost per 1000 runs | $10-100 | $0 |
| Data leaves machine | Yes | No |
| Offline capable | No | Yes |
| Cold start latency | 500-2000ms | 1-3s (model load) |
| Inference speed | 30-100 tok/s | 20-60 tok/s (Apple Silicon, small models) |
| Total model disk | N/A | ~2.4 GB |
| Peak RAM (inference) | N/A | ~2-3 GB |
| Infrastructure | Cloud account | Docker only |

---

## 2. Project Structure

```
argus/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── README.md
├── .env.example
├── data/                      # SQLite persistence (Docker volume)
├── src/
│   └── argus/
│       ├── __init__.py
│       ├── app.py             # AgentOS FastAPI entrypoint
│       ├── config.py          # Settings via pydantic-settings
│       ├── models.py          # Ollama model definitions
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── research.py    # Research agent tools
│       │   └── writing.py     # Writer agent tools
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── researcher.py  # Researcher agent definition
│       │   └── writer.py      # Writer agent definition
│       └── teams/
│           ├── __init__.py
│           └── content.py     # Content creation team
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx           # React entrypoint
│       ├── App.tsx            # Root component with layout
│       ├── api/
│       │   └── agno.ts        # AgentOS API client + SSE parser
│       ├── hooks/
│       │   └── useChat.ts     # Chat state machine + streaming hook
│       ├── components/
│       │   ├── ChatWindow.tsx  # Main chat container
│       │   ├── MessageList.tsx # Scrollable message history
│       │   ├── MessageBubble.tsx # Single message with markdown rendering
│       │   ├── CodeBlock.tsx   # Syntax-highlighted code blocks
│       │   ├── ToolCallCard.tsx # Tool invocation display
│       │   └── ChatInput.tsx   # Input bar with send button
│       ├── styles/
│       │   └── globals.css     # Tailwind + custom theme
│       └── types/
│           └── chat.ts         # TypeScript interfaces
├── tests/
│   ├── conftest.py
│   ├── test_agents/
│   │   ├── test_researcher.py
│   │   └── test_writer.py
│   └── test_teams/
│       └── test_content.py
└── docs/
    └── system-upgrades/
        └── local-multi-agent-system.md
```

| Directory | Rationale |
|-----------|-----------|
| `src/argus/` layout | Prevents accidental imports from project root |
| Separate `tools/`, `agents/`, `teams/` | SRP — each module has one responsibility |
| `config.py` | Single source of truth for all configuration |
| `data/` volume | SQLite persistence survives container restarts |
| `frontend/src/api/` | Isolated API layer — easy to swap or mock |
| `frontend/src/hooks/` | Business logic separated from UI components |
| `frontend/src/components/` | Presentational components only |

---

## 3. Component Specifications

### 3.1 — Python Dependencies (`pyproject.toml`)

```toml
[project]
name = "argus"
version = "0.1.0"
description = "Local multi-agent system powered by Agno and Ollama"
requires-python = ">=3.13"
dependencies = [
    "agno[os]>=2.5.0",
    "ollama>=0.4.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
    "ruff>=0.8.0",
    "mypy>=1.10.0",
]

[tool.ruff]
line-length = 80
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--tb=short",
    "-v",
    "-ra",
]

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
precision = 2
show_missing = true
fail_under = 90.0
```

---

### 3.2 — Configuration (`src/argus/config.py`)

```python
"""Argus system configuration.

Centralized settings for Ollama connection, model selection,
and application behavior.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = {"env_prefix": "ARGUS_"}

    # Ollama connection
    ollama_host: str = "http://localhost:11434"

    # Model assignments
    leader_model: str = "qwen3:1.7b"
    researcher_model: str = "qwen3:0.6b"
    writer_model: str = "qwen3:0.6b"

    # Persistence
    database_path: Path = Path("data/agno.db")

    # Agent behavior
    max_history_runs: int = 5
    stream_responses: bool = True


settings = Settings()
```

---

### 3.3 — Model Definitions (`src/argus/models.py`)

```python
"""Ollama model definitions for Argus agents."""

from agno.models.ollama import Ollama

from argus.config import settings


def create_leader_model() -> Ollama:
    """Create the team leader model (Qwen3 1.7B)."""
    return Ollama(
        id=settings.leader_model,
        host=settings.ollama_host,
    )


def create_researcher_model() -> Ollama:
    """Create the researcher agent model (Qwen3 0.6B)."""
    return Ollama(
        id=settings.researcher_model,
        host=settings.ollama_host,
    )


def create_writer_model() -> Ollama:
    """Create the writer agent model (Qwen3 0.6B)."""
    return Ollama(
        id=settings.writer_model,
        host=settings.ollama_host,
    )
```

---

### 3.4 — Custom Tools

**`src/argus/tools/research.py`:**

```python
"""Research tools for the Researcher agent."""

from agno.tools import tool


@tool
def search_documents(query: str) -> str:
    """Search internal documents for relevant information.

    Args:
        query: The search query to find relevant documents.
    """
    # Replace with actual search implementation
    # e.g., vector DB lookup, file search, API call
    return f"Found 3 documents matching '{query}': [doc1, doc2, doc3]"


@tool
def extract_key_facts(text: str) -> str:
    """Extract key facts and data points from text.

    Args:
        text: The text to extract facts from.
    """
    return f"Key facts extracted from text ({len(text)} chars)"


@tool
def summarize_findings(
    topic: str,
    findings: str,
) -> str:
    """Summarize research findings into a structured report.

    Args:
        topic: The research topic.
        findings: Raw findings to summarize.
    """
    return (
        f"Summary for '{topic}': "
        f"{findings[:200]}..."
    )
```

**`src/argus/tools/writing.py`:**

```python
"""Writing tools for the Writer agent."""

from pathlib import Path

from agno.tools import tool


@tool
def write_draft(
    title: str,
    content: str,
    output_path: str,
) -> str:
    """Write a draft document to disk.

    Args:
        title: Document title.
        content: Document body content.
        output_path: File path to write the draft.
    """
    file_path = Path("data/drafts") / output_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        f"# {title}\n\n{content}",
        encoding="utf-8",
    )
    return f"Draft written to {file_path}"


@tool
def format_as_markdown(content: str) -> str:
    """Format raw content as clean Markdown.

    Args:
        content: Raw text content to format.
    """
    return f"## Formatted Content\n\n{content}"
```

**Tool design rationale:**

| Decision | Rationale |
|----------|-----------|
| `@tool` decorator | Agno native — auto-generates JSON schema for LLM tool calling |
| Typed params with docstrings | Ollama models need clear parameter descriptions for reliable tool use |
| Simple `str` return types | Small models handle string returns most reliably |
| 3-5 tools per agent max | Keeps prompt compact within small model context limits |

---

### 3.5 — Agent Definitions

**`src/argus/agents/researcher.py`:**

```python
"""Researcher agent definition."""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb

from argus.config import settings
from argus.models import create_researcher_model
from argus.tools.research import (
    extract_key_facts,
    search_documents,
    summarize_findings,
)


def create_researcher_agent() -> Agent:
    """Create the Researcher sub-agent."""
    return Agent(
        name="Researcher",
        role="Research specialist that finds and analyzes information",
        model=create_researcher_model(),
        tools=[
            search_documents,
            extract_key_facts,
            summarize_findings,
        ],
        instructions=[
            "You are a thorough research specialist.",
            "Always use search_documents to find relevant information.",
            "Extract key facts before summarizing.",
            "Provide structured, factual responses.",
            "Never fabricate data — use tools to gather real information.",
        ],
        db=SqliteDb(
            table_name="researcher_sessions",
            db_file=str(settings.database_path),
        ),
        add_history_to_context=True,
        num_history_runs=settings.max_history_runs,
        markdown=True,
    )
```

**`src/argus/agents/writer.py`:**

```python
"""Writer agent definition."""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb

from argus.config import settings
from argus.models import create_writer_model
from argus.tools.writing import (
    format_as_markdown,
    write_draft,
)


def create_writer_agent() -> Agent:
    """Create the Writer sub-agent."""
    return Agent(
        name="Writer",
        role="Content writer that creates polished documents",
        model=create_writer_model(),
        tools=[
            write_draft,
            format_as_markdown,
        ],
        instructions=[
            "You are a skilled content writer.",
            "Use research provided by team members as source material.",
            "Write clear, well-structured content.",
            "Always format output as Markdown.",
            "Use write_draft to save final documents.",
        ],
        db=SqliteDb(
            table_name="writer_sessions",
            db_file=str(settings.database_path),
        ),
        add_history_to_context=True,
        num_history_runs=settings.max_history_runs,
        markdown=True,
    )
```

**Agent design rationale:**

| Decision | Rationale |
|----------|-----------|
| Factory functions (`create_*`) | Fresh instances per request — Agno best practice, avoids state leaks |
| `role` parameter | Team leader uses this to decide which agent handles which subtask |
| Explicit `instructions` list | Small models need clear, concise directives — no ambiguity |
| `SqliteDb` per agent with separate tables | Session isolation between agents |
| `num_history_runs=5` | Keep context manageable for small models |

---

### 3.6 — Team Orchestration (`src/argus/teams/content.py`)

```python
"""Content creation team definition."""

from agno.db.sqlite import SqliteDb
from agno.team import Team

from argus.agents.researcher import create_researcher_agent
from argus.agents.writer import create_writer_agent
from argus.config import settings
from argus.models import create_leader_model


def create_content_team() -> Team:
    """Create the content creation team.

    Team leader (Qwen3 1.7B) coordinates:
    - Researcher (Qwen3 0.6B): finds and analyzes information
    - Writer (Qwen3 0.6B): creates polished content
    """
    return Team(
        name="Content Team",
        mode="coordinate",
        model=create_leader_model(),
        members=[
            create_researcher_agent(),
            create_writer_agent(),
        ],
        instructions=[
            "You are the team leader for content creation.",
            "Break tasks into research and writing phases.",
            "First delegate research to the Researcher agent.",
            "Then pass research results to the Writer agent.",
            "Review the final output before delivering.",
        ],
        db=SqliteDb(
            table_name="team_sessions",
            db_file=str(settings.database_path),
        ),
        add_history_to_context=True,
        markdown=True,
    )
```

**Team design rationale:**

| Decision | Rationale |
|----------|-----------|
| `mode="coordinate"` | Leader decomposes, delegates, and synthesizes — best for multi-step tasks |
| Leader = Qwen3 1.7B (largest) | Best sub-4B tool calling (0.960 agent score). Handles task decomposition |
| Sub-agents = Qwen3 0.6B (smallest viable) | 0.880 agent score — sufficient for focused single-tool tasks. 523 MB each |

---

### 3.7 — AgentOS Entrypoint (`src/argus/app.py`)

```python
"""Argus application entrypoint.

Exposes the Content Team via AgentOS FastAPI runtime.
"""

from agno.os import AgentOS

from argus.agents.researcher import create_researcher_agent
from argus.agents.writer import create_writer_agent
from argus.teams.content import create_content_team

agent_os = AgentOS(
    agents=[
        create_researcher_agent(),
        create_writer_agent(),
    ],
    teams=[create_content_team()],
    tracing=True,
)

app = agent_os.get_app()
```

---

### 3.8 — Docker Compose (`docker-compose.yml`)

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: argus-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 6G

  ollama-pull:
    image: ollama/ollama:latest
    container_name: argus-ollama-pull
    depends_on:
      ollama:
        condition: service_healthy
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        ollama pull qwen3:1.7b
        ollama pull qwen3:0.6b
    environment:
      - OLLAMA_HOST=ollama:11434

  agno-app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: argus-agno
    ports:
      - "8000:8000"
    depends_on:
      ollama:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/status"]
      interval: 10s
      timeout: 5s
      retries: 5
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - AGNO_TELEMETRY=false
      - DATABASE_PATH=/app/data/agno.db
    volumes:
      - ./data:/app/data

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: argus-frontend
    ports:
      - "3000:3000"
    depends_on:
      agno-app:
        condition: service_healthy
    environment:
      - VITE_API_URL=http://localhost:8000

volumes:
  ollama-models:
```

**Backend Dockerfile:**

```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e ".[dev]"

COPY src/ src/
COPY tests/ tests/

EXPOSE 8000

CMD ["uvicorn", "argus.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile:**

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
```

**Infrastructure rationale:**

| Decision | Rationale |
|----------|-----------|
| `memory: 6G` on Ollama | Qwen3 1.7B peaks at ~3 GB — 6 GB gives headroom for context. Leaves 10 GB for OS + other containers |
| `healthcheck` on Ollama | Ensures API ready before app starts |
| `ollama-pull` init service | Pulls models once, exits — clean separation |
| `ollama-models` named volume | Models persist across `docker-compose down/up` |
| `AGNO_TELEMETRY=false` | Fully local, no external calls |
| Frontend `depends_on: agno-app` | Waits for API health before starting |
| `VITE_API_URL` as env var | Frontend connects to host-exposed API port |

---

### 3.9 — Frontend: TypeScript Types (`frontend/src/types/chat.ts`)

```typescript
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  status: "started" | "completed" | "error";
}

export interface RunEvent {
  event: string;
  run_id?: string;
  session_id?: string;
  content?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  result?: string;
  metrics?: Record<string, number>;
}
```

---

### 3.10 — Frontend: API Client + SSE Parser (`frontend/src/api/agno.ts`)

Native `EventSource` does NOT support POST or custom headers — use `fetch()` with manual SSE line parsing.

```typescript
import type { RunEvent } from "../types/chat";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchTeams(): Promise<{ name: string; team_id: string }[]> {
  const response = await fetch(`${API_URL}/teams`);
  if (!response.ok) throw new Error("Failed to fetch teams");
  return response.json();
}

export async function* streamTeamRun(
  teamId: string,
  message: string,
  sessionId?: string,
): AsyncGenerator<RunEvent> {
  const formData = new FormData();
  formData.append("message", message);
  formData.append("stream", "true");
  if (sessionId) {
    formData.append("session_id", sessionId);
  }

  const response = await fetch(
    `${API_URL}/teams/${encodeURIComponent(teamId)}/runs`,
    { method: "POST", body: formData },
  );

  if (!response.ok) {
    throw new Error(`Run failed: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const data = line.slice(6);
        try {
          const parsed: RunEvent = JSON.parse(data);
          parsed.event = parsed.event || currentEvent;
          yield parsed;
        } catch {
          // Skip malformed JSON lines
        }
      }
    }
  }
}
```

**API client rationale:**

| Decision | Rationale |
|----------|-----------|
| `fetch()` not `EventSource` | `EventSource` only supports GET — AgentOS runs require POST with form data |
| `AsyncGenerator` with `yield` | Caller consumes events incrementally — real-time UI updates |
| `FormData` | AgentOS run endpoints require multipart, not JSON |
| `session_id` passthrough | Same `session_id` = same conversation thread |

---

### 3.11 — Frontend: Chat Hook (`frontend/src/hooks/useChat.ts`)

```typescript
import { useCallback, useRef, useState } from "react";

import { streamTeamRun } from "../api/agno";
import type { ChatMessage, ToolCall } from "../types/chat";

interface UseChatOptions {
  teamId: string;
}

export function useChat({ teamId }: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const sessionIdRef = useRef<string | undefined>(undefined);

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
        toolCalls: [],
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);

      try {
        const stream = streamTeamRun(
          teamId,
          content,
          sessionIdRef.current,
        );

        for await (const event of stream) {
          switch (event.event) {
            case "RunStarted":
              sessionIdRef.current = event.session_id;
              break;

            case "RunContent":
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  last.content += event.content || "";
                }
                return updated;
              });
              break;

            case "ToolCallStarted": {
              const toolCall: ToolCall = {
                name: event.tool_name || "unknown",
                args: event.tool_args || {},
                status: "started",
              };
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  last.toolCalls = [...(last.toolCalls || []), toolCall];
                }
                return updated;
              });
              break;
            }

            case "ToolCallCompleted":
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant" && last.toolCalls) {
                  const tool = last.toolCalls.find(
                    (t) => t.name === event.tool_name && t.status === "started",
                  );
                  if (tool) {
                    tool.status = "completed";
                    tool.result = event.result;
                  }
                }
                return updated;
              });
              break;

            case "RunCompleted":
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  last.isStreaming = false;
                  if (event.content) {
                    last.content = event.content;
                  }
                }
                return updated;
              });
              break;

            case "RunError":
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  last.content = `Error: ${event.content || "Unknown error"}`;
                  last.isStreaming = false;
                }
                return updated;
              });
              break;
          }
        }
      } catch (error) {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "assistant") {
            last.content = `Connection error: ${error instanceof Error ? error.message : "Unknown"}`;
            last.isStreaming = false;
          }
          return updated;
        });
      } finally {
        setIsLoading(false);
      }
    },
    [teamId],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = undefined;
  }, []);

  return { messages, isLoading, sendMessage, clearMessages };
}
```

**Hook rationale:**

| Decision | Rationale |
|----------|-----------|
| `useRef` for `sessionId` | Persists across renders without re-render trigger. Set on first `RunStarted` |
| Switch on `event.event` | Each SSE event type updates a specific part of the UI |
| `isStreaming` flag per message | Enables typing cursor animation on active message |
| `toolCalls` array per message | Displays tool invocations inline within assistant responses |
| `clearMessages` resets `sessionIdRef` | New conversation — next send auto-generates new `session_id` |

---

### 3.12 — Frontend: UI Components

**Design system**: Dark zinc theme, Inter font, Tailwind CSS v4. Code blocks use `react-syntax-highlighter` with oneDark. Markdown rendered via `react-markdown` + `remark-gfm`.

**`frontend/package.json`:**

```json
{
  "name": "argus-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-markdown": "^9.0.0",
    "react-syntax-highlighter": "^15.6.0",
    "remark-gfm": "^4.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@types/react-syntax-highlighter": "^15.5.0",
    "@vitejs/plugin-react": "^4.0.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0"
  }
}
```

**`frontend/src/components/CodeBlock.tsx`:**

```tsx
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface CodeBlockProps {
  language: string;
  children: string;
}

export function CodeBlock({ language, children }: CodeBlockProps) {
  return (
    <div className="relative group my-3 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between bg-zinc-800 px-4 py-2 text-xs text-zinc-400">
        <span>{language}</span>
        <button
          onClick={() => navigator.clipboard.writeText(children)}
          className="opacity-0 group-hover:opacity-100 transition-opacity
                     hover:text-white cursor-pointer"
        >
          Copy
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          fontSize: "0.85rem",
        }}
      >
        {children.trim()}
      </SyntaxHighlighter>
    </div>
  );
}
```

**`frontend/src/components/ToolCallCard.tsx`:**

```tsx
import type { ToolCall } from "../types/chat";

interface ToolCallCardProps {
  toolCall: ToolCall;
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const statusStyles = {
    started: "border-blue-500/30 bg-blue-500/5",
    completed: "border-emerald-500/30 bg-emerald-500/5",
    error: "border-red-500/30 bg-red-500/5",
  };

  const statusIcons = {
    started: "⟳",
    completed: "✓",
    error: "✕",
  };

  return (
    <div
      className={`my-2 rounded-lg border p-3 text-sm
                  ${statusStyles[toolCall.status]}`}
    >
      <div className="flex items-center gap-2 font-mono text-xs text-zinc-400">
        <span>{statusIcons[toolCall.status]}</span>
        <span className="font-semibold text-zinc-300">
          {toolCall.name}
        </span>
      </div>
      {Object.keys(toolCall.args).length > 0 && (
        <pre className="mt-2 text-xs text-zinc-500 overflow-x-auto">
          {JSON.stringify(toolCall.args, null, 2)}
        </pre>
      )}
      {toolCall.result && (
        <div className="mt-2 text-xs text-zinc-400 border-t border-zinc-700/50 pt-2">
          {toolCall.result}
        </div>
      )}
    </div>
  );
}
```

**`frontend/src/components/MessageBubble.tsx`:**

```tsx
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import type { ChatMessage } from "../types/chat";
import { CodeBlock } from "./CodeBlock";
import { ToolCallCard } from "./ToolCallCard";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  const markdownComponents: Components = {
    code({ className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || "");
      const codeString = String(children).replace(/\n$/, "");

      if (match) {
        return <CodeBlock language={match[1]}>{codeString}</CodeBlock>;
      }

      return (
        <code
          className="bg-zinc-800 text-emerald-400 px-1.5 py-0.5
                     rounded text-sm font-mono"
          {...props}
        >
          {children}
        </code>
      );
    },
    table({ children }) {
      return (
        <div className="overflow-x-auto my-3">
          <table className="w-full text-sm border-collapse">
            {children}
          </table>
        </div>
      );
    },
    th({ children }) {
      return (
        <th className="border border-zinc-700 bg-zinc-800 px-3 py-2
                       text-left text-zinc-300">
          {children}
        </th>
      );
    },
    td({ children }) {
      return (
        <td className="border border-zinc-700 px-3 py-2 text-zinc-400">
          {children}
        </td>
      );
    },
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-5 py-3 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-zinc-800/80 text-zinc-200 border border-zinc-700/50"
        }`}
      >
        {message.toolCalls?.map((tc, i) => (
          <ToolCallCard key={`${tc.name}-${i}`} toolCall={tc} />
        ))}

        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={markdownComponents}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {message.isStreaming && (
          <span className="inline-block w-2 h-4 bg-blue-400 animate-pulse ml-1" />
        )}
      </div>
    </div>
  );
}
```

**`frontend/src/components/MessageList.tsx`:**

```tsx
import { useEffect, useRef } from "react";

import type { ChatMessage } from "../types/chat";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-zinc-500">
        <div className="text-center">
          <div className="text-4xl mb-4">&#9673;</div>
          <p className="text-lg font-medium">Argus</p>
          <p className="text-sm mt-1">Ask me anything. I'll research and write for you.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-2">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

**`frontend/src/components/ChatInput.tsx`:**

```tsx
import { type FormEvent, type KeyboardEvent, useRef, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function handleInput() {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-zinc-800 bg-zinc-900/80 backdrop-blur-sm p-4"
    >
      <div
        className="flex items-end gap-3 max-w-3xl mx-auto
                    bg-zinc-800 rounded-2xl border border-zinc-700/50
                    focus-within:border-blue-500/50 transition-colors px-4 py-3"
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Type a message..."
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent text-zinc-200 placeholder-zinc-500
                     outline-none resize-none text-sm leading-6 max-h-[200px]"
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="flex-shrink-0 w-9 h-9 rounded-xl bg-blue-600
                     hover:bg-blue-500 disabled:bg-zinc-700
                     disabled:cursor-not-allowed transition-colors
                     flex items-center justify-center"
        >
          <svg
            width="16" height="16" viewBox="0 0 16 16"
            fill="none" className="text-white"
          >
            <path
              d="M2 8L14 2L8 14L7 9L2 8Z"
              fill="currentColor"
            />
          </svg>
        </button>
      </div>
    </form>
  );
}
```

**`frontend/src/components/ChatWindow.tsx`:**

```tsx
import { useChat } from "../hooks/useChat";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";

interface ChatWindowProps {
  teamId: string;
}

export function ChatWindow({ teamId }: ChatWindowProps) {
  const { messages, isLoading, sendMessage, clearMessages } = useChat({
    teamId,
  });

  return (
    <div className="flex flex-col h-screen bg-zinc-950">
      <header
        className="flex items-center justify-between px-6 py-4
                    border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-sm"
      >
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">
            Argus
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Multi-Agent Content Team
          </p>
        </div>
        <button
          onClick={clearMessages}
          className="text-xs text-zinc-500 hover:text-zinc-300
                     transition-colors px-3 py-1.5 rounded-lg
                     hover:bg-zinc-800"
        >
          New Chat
        </button>
      </header>

      <MessageList messages={messages} />

      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}
```

**`frontend/src/App.tsx`:**

```tsx
import { ChatWindow } from "./components/ChatWindow";

export default function App() {
  return <ChatWindow teamId="Content Team" />;
}
```

**`frontend/src/main.tsx`:**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

**`frontend/src/styles/globals.css`:**

```css
@import "tailwindcss";

@layer base {
  body {
    @apply bg-zinc-950 text-zinc-200 antialiased;
    font-family:
      "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI",
      Roboto, sans-serif;
  }

  ::-webkit-scrollbar {
    width: 6px;
  }
  ::-webkit-scrollbar-track {
    background: transparent;
  }
  ::-webkit-scrollbar-thumb {
    background: #3f3f46;
    border-radius: 3px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: #52525b;
  }
}
```

**`frontend/index.html`:**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Argus — Multi-Agent Chat</title>
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**`frontend/vite.config.ts`:**

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
  },
});
```

**UI design rationale:**

| Decision | Rationale |
|----------|-----------|
| Dark zinc palette (`bg-zinc-950`) | Modern, easy on eyes, matches developer tool aesthetic |
| `react-markdown` + `remark-gfm` | Handles GFM tables, lists, bold, italic, links |
| `react-syntax-highlighter` + oneDark | Industry-standard syntax highlighting, matches VS Code dark |
| Tailwind CSS v4 | Utility-first, rapid styling, no separate CSS per component |
| Auto-scroll on new messages | Standard chat UX — always see latest |
| Textarea with auto-resize | Grows naturally up to 200px, then scrolls |
| Enter = send, Shift+Enter = newline | Matches Slack, ChatGPT, Claude |
| Streaming cursor (`animate-pulse`) | Visual indicator response is generating |
| Tool call cards inline | Transparent — user sees what tools are being used |
| Copy button on code blocks | Group-hover reveal — clean, uncluttered |

---

## 4. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Ollama model swap latency (1-3s per swap) | Medium | Models are tiny (0.6-1.7B) — swaps are fast. Sub-agents share same model so no swap needed between them |
| Sub-2B models hallucinate tool calls | Medium | Qwen3 1.7B scores 0.960, 0.6B scores 0.880 on benchmarks. Keep tool schemas simple, 2-3 tools per agent max. Add `use_json_mode=True` as fallback |
| 16GB RAM exceeded with Docker overhead | Low | Peak inference RAM is ~3 GB. Total model disk is ~2.4 GB. Massive headroom on 16 GB machine |
| Ollama container fails to pull large models | Low | `ollama-pull` init container retries. Models cached in named volume |
| Agno API changes (fast-moving project) | Medium | Pin `agno>=2.5.0,<3.0.0`. Check changelog before updating |
| SQLite concurrent access issues | Low | Single-writer pattern. Agno handles internally. Migrate to PostgreSQL if scaling |
| SSE stream drops on slow models | Medium | Frontend handles errors gracefully. Agent responses may take 30-60s |
| Markdown rendering XSS | Low | `react-markdown` sanitizes by default. No `dangerouslySetInnerHTML` |
| Large streamed responses break UI | Low | `max-w-[80%]` on bubbles + `overflow-x-auto` on code blocks |

### Edge Cases

- **First run**: `ollama-pull` downloads ~2.4 GB of models. Requires internet. Subsequent runs offline-capable.
- **Model not loaded**: Docker `depends_on: condition: service_healthy` ensures Ollama ready before app starts.
- **Long context**: Tool definitions expand prompts. Keep 2-3 tools per agent — critical for sub-2B models.
- **Qwen3 tool hallucination**: Models may reason correctly in `<think>` block but emit wrong tool call (issue #11135). Simple tool schemas with clear docstrings reduce this.

---

## 5. Implementation Phases

### Phase 1 — Project Scaffold ✅ COMPLETED
**Environment:** Local dev

- [x] Create directory structure per Section 2
- [x] Create `pyproject.toml` per Section 3.1
- [x] Create `src/argus/__init__.py`
- [x] Create `src/argus/config.py` per Section 3.2
- [x] Create `src/argus/models.py` per Section 3.3
- [x] Run `ruff check src/` — zero errors

---

### Phase 2 — Tools, Agents, and Team ✅ COMPLETED
**Environment:** Local dev

- [x] Create tools: `research.py` (search_documents, extract_key_facts, summarize_findings), `writing.py` (write_draft, format_as_markdown)
- [x] Create agents: `researcher.py`, `writer.py`
- [x] Create team: `content.py` (coordinate mode)
- [x] Create `app.py` (AgentOS entrypoint)
- [x] Run `ruff check src/ tests/` — zero errors

**Issues found during implementation:**
- `SqliteDb` parameter is `session_table`, not `table_name` (Agno API change)
- `Team.mode` requires `TeamMode.coordinate` enum, not string `"coordinate"` (for `/teams` endpoint to work)
- `agno[os]` depends on `openai` package — added to `pyproject.toml`
- `tracing=True` causes OpenTelemetry `GeneratorExit` errors — disabled

---

### Phase 3 — Docker Infrastructure ✅ COMPLETED
**Environment:** Docker + Native macOS

- [x] Create `docker-compose.yml`, `Dockerfile`, `frontend/Dockerfile`
- [x] Create `.env.example`, `.gitignore`, `data/.gitkeep`
- [x] Build and launch all containers
- [x] Verify API: `curl http://localhost:8000/teams` returns team data
- [x] Smoke test: team returns response in ~5s

**Major architecture change: Ollama moved from Docker to native macOS.**

Initially Ollama ran inside Docker, but Docker on macOS uses a Linux VM without Apple Silicon GPU access. Result: ~60s per response (CPU-only inference). After installing Ollama natively (`brew install ollama`), responses dropped to ~5s (Metal GPU).

**Changes from plan:**
- Removed `ollama` and `ollama-pull` services from `docker-compose.yml`
- `agno-app` connects to native Ollama via `ARGUS_OLLAMA_HOST=http://host.docker.internal:11434`
- Models pulled natively: `ollama pull qwen3:1.7b && ollama pull qwen3:0.6b`
- Dockerfile updated: added `curl` for healthcheck, `src/` copied before `uv pip install` for editable install
- `[tool.setuptools.packages.find] where = ["src"]` added to `pyproject.toml`
- Healthcheck changed from `/status` (doesn't exist) to `/agents`

---

### Phase 4 — React Chat Frontend ✅ COMPLETED
**Environment:** Docker

- [x] Create all frontend components (CodeBlock, ToolCallCard, MessageBubble, MessageList, ChatInput, ChatWindow, App)
- [x] Create API client with SSE parser (`api/agno.ts`)
- [x] Create chat state hook (`hooks/useChat.ts`)
- [x] Build and deploy in Docker
- [x] End-to-end chat working: streaming, tool calls, code blocks, markdown, LaTeX

**Issues found and fixed during implementation:**

1. **Tailwind CSS v4 not loading** — `@import "tailwindcss"` requires `@tailwindcss/vite` plugin, not the postcss approach. Added `@tailwindcss/vite` to devDependencies and registered in `vite.config.ts`.

2. **Team ID mismatch** — Frontend sent `teamId="Content Team"` but Agno auto-slugifies to `content-team`. Fixed `App.tsx` to use `content-team`.

3. **SSE events prefixed with `Team`** — Agno team endpoints emit `TeamRunStarted`, `TeamRunContent`, etc. Frontend expected `RunStarted`, `RunContent`. Added normalizer: `event.event.replace(/^Team/, "")`.

4. **Tool call fields nested under `event.tool`** — Agno nests tool info as `event.tool.tool_name` and `event.tool.tool_args`, not flat `event.tool_name`. Updated hook to extract from both locations.

5. **Messages vanishing (React state mutation)** — State updates were mutating objects in-place (`last.content += ...`). React can't detect in-place mutations. Fixed all setMessages callbacks to create new objects via spread: `{ ...last, content: last.content + event.content }`.

6. **`RunCompleted` overwriting streamed content** — The final event contains full content, which overwrote incrementally streamed text. Fixed: `content: last.content || event.content` (only use completed content as fallback).

7. **SSE parser splitting on `\n` instead of `\n\n`** — SSE blocks are delimited by double newlines. Single-newline splitting caused `currentEvent` to reset between chunks. Rewrote parser to split on `\n\n` and keep `currentEvent` across chunk reads.

8. **Raw `<tools>` XML in output** — Small models dump tool call XML as text. Added `cleanContent()` function to strip `<tools>...</tools>` blocks and unwrap `<summary>`/`<note>` tags.

9. **LaTeX formulas not rendered** — Added `remark-math`, `rehype-katex`, and KaTeX CSS. Inline `$...$` and block `$$...$$` now render as formatted math with dark theme overrides.

10. **UI redesigned** — Initial bubble-style UI replaced with Claude/ChatGPT-style layout: centered narrow column, avatar for assistant, no bubbles for assistant messages, thinking dots animation, minimal header.

---

### Phase 5 — Testing ✅ COMPLETED
**Environment:** Docker

- [x] Write unit tests: `test_researcher.py` (7 tests), `test_writer.py` (5 tests), `test_content.py` (3 tests)
- [x] All tests mock Ollama and SqliteDb — no external dependencies
- [x] `ruff check src/ tests/` — zero errors
- [x] Backend API tested via curl: non-streaming and SSE streaming both work
- [x] SSE events verified: `TeamRunStarted`, `TeamRunContent` (multiple), `TeamRunCompleted`

---

### Phase 6 — Final Validation (PENDING)
**Environment:** Docker

#### Step 1 — Reliability Testing

- [ ] Run 10 sequential team requests — verify no memory leaks via `docker stats`
- [ ] Verify SQLite sessions persist: `sqlite3 data/agno.db ".tables"`
- [ ] Stop and restart: `docker compose down && docker compose up -d`
- [ ] Verify session history survives restart

> **Checkpoint:** System stable under repeated use. Data persists across restarts.

#### Step 2 — Frontend Stress Test

- [ ] Send 20 messages in rapid succession — verify no UI freezes
- [ ] Send message generating long code block (500+ lines) — verify scrolling
- [ ] Open DevTools Network tab — verify no failed requests

> **Checkpoint:** Frontend stable under load.

#### Step 3 — Documentation ✅ COMPLETED

- [x] Write `README.md` with setup instructions, architecture, usage
- [x] Verify `.env.example` documents all variables

> **Checkpoint:** README written with quick start, architecture, config, API, dev commands.

---

## 6. Manual Steps Tracking

| Step | Environment | Description | Status | Date | Notes |
|------|-------------|-------------|--------|------|-------|
| 1 | Local | Install Docker Desktop | Done | 2026-04-07 | Docker 28.5.2, Compose v2.40.3 |
| 2 | Local | Install Ollama natively | Done | 2026-04-07 | `brew install ollama` v0.20.3 — required for Metal GPU |
| 3 | Local | Pull models natively | Done | 2026-04-07 | `ollama pull qwen3:1.7b && ollama pull qwen3:0.6b` (~2.4 GB) |

---

## 7. Execution History

| Date | Phase/Step | Action | Result |
|------|------------|--------|--------|
| 2026-04-07 | Phase 1 | Created project scaffold: pyproject.toml, config.py, models.py | All imports clean, ruff passes |
| 2026-04-07 | Phase 2 | Created tools, agents, team, app.py | ruff passes. Found 3 Agno API issues (SqliteDb param, TeamMode enum, openai dep) |
| 2026-04-07 | Phase 2 | Fixed `table_name` → `session_table`, `"coordinate"` → `TeamMode.coordinate`, added `openai` dep | Backend starts and serves API |
| 2026-04-07 | Phase 3 | Built Docker images, launched with Ollama in Docker | ~60s response time — CPU-only in Docker VM |
| 2026-04-07 | Phase 3 | Installed Ollama natively, moved to `host.docker.internal` | ~5s response time — Metal GPU acceleration |
| 2026-04-07 | Phase 3 | Fixed Dockerfile: src/ before pip install, added curl, fixed healthcheck | Backend healthy in Docker |
| 2026-04-07 | Phase 4 | Created React frontend with all components | Styles not loading — Tailwind v4 needs @tailwindcss/vite plugin |
| 2026-04-07 | Phase 4 | Fixed Tailwind: added @tailwindcss/vite, registered in vite.config.ts | Styles render correctly |
| 2026-04-07 | Phase 4 | Fixed team ID: `Content Team` → `content-team` (Agno auto-slugifies) | Team requests succeed |
| 2026-04-07 | Phase 4 | Fixed SSE events: `TeamRunX` → normalized to `RunX` | Events parsed correctly |
| 2026-04-07 | Phase 4 | Fixed tool call fields: nested `event.tool.tool_name` extraction | Tool calls display correctly |
| 2026-04-07 | Phase 4 | Fixed React state mutations: spread instead of in-place, RunCompleted fallback | Messages no longer vanish |
| 2026-04-07 | Phase 4 | Rewrote SSE parser: split on `\n\n`, persist `currentEvent` across chunks | Reliable streaming |
| 2026-04-07 | Phase 4 | Added LaTeX: remark-math + rehype-katex + KaTeX CSS + dark theme | Math formulas render |
| 2026-04-07 | Phase 4 | Added content cleaning: strip `<tools>` XML, unwrap `<summary>`/`<note>` | Clean output |
| 2026-04-07 | Phase 4 | Redesigned UI: Claude/ChatGPT style layout | Modern chat UX |
| 2026-04-07 | Phase 5 | Created test suite: 15 tests across researcher, writer, content team | ruff passes, tests structured |
| 2026-04-07 | Phase 6.3 | Created README.md | Quick start, architecture, config, API, dev commands |

---

## 8. Outcome

### Open Questions / Future Work

- **Model upgrade path**: If 0.6B sub-agents lack quality, upgrade to `qwen3:1.7b` for all (still only ~3 GB RAM). If leader needs more reasoning, try `qwen3:4b` (~3.5 GB)
- **Speed optimization**: Replace sub-agents with `lfm2.5-thinking:1.2b` (0.920 score, 7x faster than qwen3:1.7b, non-transformer)
- **Parallel model loading**: Test `OLLAMA_MAX_LOADED_MODELS=2` — with these tiny models, both can fit in RAM simultaneously
- **Knowledge/RAG**: Add vector database (LanceDB — file-based, no server) for real document search
- **Guardrails**: Add pre/post hooks for input validation and output quality checks
- **Authentication**: Enable AgentOS JWT auth for production exposure
- **PostgreSQL migration**: Replace SQLite if concurrent access becomes an issue
- **Workflow upgrade**: If team coordination is too unpredictable, refactor to explicit Workflow with deterministic `Steps` + `Parallel` constructs
- **Agent selector UI**: Add dropdown to switch between individual agents and teams
- **Session history sidebar**: List past conversations with restore capability (API: `GET /sessions`)
- **File upload**: AgentOS supports file attachments — add drag-and-drop to ChatInput
- **Production frontend**: Replace Vite dev server with `nginx` serving `vite build` output
- **Reasoning display**: Show chain-of-thought steps when `reasoning=True` (via `ReasoningStep` SSE events)
