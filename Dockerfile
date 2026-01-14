# syntax=docker/dockerfile:1

# ============================================
# Base image avec uv et dépendances
# ============================================
FROM python:3.13-slim AS base

# Installation de uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Variables d'environnement pour Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copie des fichiers de dépendances
COPY pyproject.toml uv.lock ./

# Installation des dépendances
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copie du code source
COPY src/ ./src/
COPY resources/ ./resources/

# Création d'un utilisateur non-root pour la sécurité
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser && \
    chown -R appuser:appgroup /app

# ============================================
# Target: MCP Server
# ============================================
FROM base AS mcp-server

# Variables d'environnement par défaut pour le serveur MCP
ENV MCP_SERVER_PORT=12345 \
    MCP_SERVER_NAME=movies-mcp-server

# Exposition du port
EXPOSE ${MCP_SERVER_PORT}

# Utilisateur non-root
USER appuser

# Healthcheck pour Kubernetes
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${MCP_SERVER_PORT}/mcp')" || exit 1

# Commande de démarrage
CMD ["uv", "run", "python", "src/mcp_tool_server.py"]

# ============================================
# Target: Agent
# ============================================
FROM base AS agent

# Variables d'environnement par défaut pour l'agent
ENV LLM_BASE_URL=http://127.0.0.1:1234/v1 \
    LLM_MODEL=openai/gpt-oss-20b \
    LLM_TEMPERATURE=0.3 \
    LLM_API_KEY=not-needed \
    MCP_CONFIG_PATH=/app/resources/servers.json \
    DEBUG=false

# Utilisateur non-root
USER appuser

# Commande de démarrage
CMD ["uv", "run", "python", "src/run_agent.py"]
