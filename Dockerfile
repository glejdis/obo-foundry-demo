# Dockerfile — Aldi Store Ops MCP server (streamable-HTTP) for Azure Container Apps.
# Build context is the repo root so we can include the shared auth.py / obo.py.
FROM python:3.12-slim

WORKDIR /app

COPY mcp_server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Shared OBO helpers (imported by the server via parent path).
COPY auth.py obo.py ./
COPY mcp_server/server.py ./mcp_server/server.py

ENV PORT=8000
EXPOSE 8000

CMD ["python", "mcp_server/server.py"]
