FROM ghcr.io/github/github-mcp-server:latest AS github-mcp-server

FROM python:3.11-slim

WORKDIR /app

COPY --from=github-mcp-server /server/github-mcp-server /usr/local/bin/github-mcp-server

RUN pip install --no-cache-dir poetry==1.8.5
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi

COPY . .

ENV PYTHONPATH=/app
