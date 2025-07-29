FROM python:3.12-slim-bullseye

# Install system dependencies in a single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

WORKDIR /src

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /bin/uv
ENV UV_PYTHON_PREFERENCE=only-system

# Copy dependency files first
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache --no-dev

USER appuser

# Install the application dependencies.
COPY --chown=appuser:appuser ./app /src/app
COPY --chown=appuser:appuser ./migrations /src/migrations
COPY --chown=appuser:appuser ./alembic.ini /src/alembic.ini
COPY --chown=appuser:appuser ./logs /src/logs

EXPOSE 5000

# Run the application.
CMD ["/src/.venv/bin/fastapi", "dev", "/src/app/main.py", "--host", "0.0.0.0", "--port", "5000"]

