FROM python:3.13-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY src/ src/

RUN uv pip install --system -e ".[dev]"

COPY tests/ tests/

EXPOSE 8000

CMD ["uvicorn", "argus.app:app", "--host", "0.0.0.0", "--port", "8000"]
