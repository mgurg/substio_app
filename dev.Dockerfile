FROM python:3.12-slim-bullseye

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

COPY --chown=appuser:appuser pyproject.toml .
COPY --chown=appuser:appuser uv.lock .
COPY --chown=appuser:appuser ./logs /src/logs

RUN uv sync --frozen --no-cache

USER appuser

# Install the application dependencies.
COPY --chown=appuser:appuser ./app /src/app
#COPY --chown=appuser:appuser ./migrations /src/migrations
#COPY --chown=appuser:appuser ./alembic.ini /src/alembic.ini

EXPOSE 5000

# Run the application.
CMD ["/src/.venv/bin/fastapi", "dev", "/src/app/main.py", "--host", "0.0.0.0", "--port", "5000"]

