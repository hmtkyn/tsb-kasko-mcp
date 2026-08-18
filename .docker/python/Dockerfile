# syntax=docker/dockerfile:1
#
# Two-stage build. The first stage resolves the locked dependency set into a
# self-contained virtual environment; the second copies only that environment
# onto a clean runtime image, so neither uv nor any build tooling ships in the
# final layer.
#
# Build from the repository root, not from this directory:
#   docker build -f .docker/python/Dockerfile -t tsb-kasko-mcp .

# Keep these in step with .python-version and with the uv pin in the CI workflow.
ARG PYTHON_VERSION=3.14
ARG UV_VERSION=0.11.33

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim-trixie AS builder

COPY --from=uv /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src

# Dependencies change far less often than source code, so install them from the
# lockfile alone first. That keeps this layer cached across source-only edits.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-default-groups --extra http

COPY . /src

# --no-editable installs a real copy of the package, so /src can be discarded.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-default-groups --extra http


FROM python:${PYTHON_VERSION}-slim-trixie AS runtime

LABEL org.opencontainers.image.title="tsb-kasko-mcp" \
      org.opencontainers.image.description="TSB Kasko Deger Listesi MCP server and CLI" \
      org.opencontainers.image.source="https://github.com/hmtkyn/tsb-kasko-mcp" \
      org.opencontainers.image.licenses="MIT"

# Unprivileged runtime user. The response cache is the only path ever written.
RUN groupadd --system --gid 1001 kasko \
    && useradd --system --uid 1001 --gid kasko --create-home kasko

COPY --from=builder --chown=kasko:kasko /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TSB_KASKO_CACHE_DIR=/home/kasko/.cache/tsb-kasko \
    TSB_KASKO_TRANSPORT=http \
    TSB_KASKO_HOST=0.0.0.0 \
    TSB_KASKO_PORT=8000

USER kasko
WORKDIR /home/kasko

EXPOSE 8000

# A TCP connect is the only check that holds for every transport: the MCP
# endpoint itself rejects requests that carry no session headers.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os,socket; socket.create_connection(('127.0.0.1', int(os.environ['TSB_KASKO_PORT'])), 3).close()"]

# Serves MCP over HTTP by default, which is what a container is useful for.
# Override the entrypoint to reach the CLI instead:
#   docker run --rm --entrypoint tsb-kasko tsb-kasko-mcp lookup 2025 "audi a3"
ENTRYPOINT ["tsb-kasko-mcp"]
