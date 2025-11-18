FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS builder
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=src,target=src \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-editable

FROM python:3.13-slim-trixie
RUN useradd seedbot -M
COPY --from=builder --chown=seedbot:seedbot /app /app

ENV PATH=/app/bin:$PATH

USER seedbot
WORKDIR /app

STOPSIGNAL SIGINT
CMD ["seedbot"]

RUN <<EOT
python -V
python -Im site
python -Ic 'import seeding_reward_bot'
EOT
