# syntax=docker/dockerfile:1.7

FROM python:3.12.12-slim-bookworm AS builder

ARG UV_VERSION=0.8.22

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install "uv==${UV_VERSION}"

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential linux-libc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


FROM python:3.12.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HUSH_SERVER_MODE=cloud \
    HF_HOME=/var/cache/hush/huggingface \
    XDG_CACHE_HOME=/var/cache/hush

RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl libgomp1 libportaudio2 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 hush \
    && useradd --uid 10001 --gid hush --create-home --shell /usr/sbin/nologin hush

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --chown=hush:hush voiceflow ./voiceflow
COPY --chown=hush:hush pyproject.toml uv.lock ./

RUN mkdir -p /app/data /var/cache/hush \
    && chown -R hush:hush /app/data /var/cache/hush

USER hush

EXPOSE 57327

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl --fail --silent http://127.0.0.1:57327/status >/dev/null || exit 1

CMD ["uvicorn", "voiceflow.web.api_server:app", "--host", "0.0.0.0", "--port", "57327", "--no-access-log"]
