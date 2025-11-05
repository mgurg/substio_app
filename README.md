# Substio_APP

## Places

- courthouse (<https://dane.gov.pl/pl/dataset/985,lista-sadow-powszechnych/resource/67369/table>)
- prison
- police

```bash
cd tools
uv run offers.py
cd ..
```

## Docker

```bash
COMPOSE_BAKE=true docker compose build
```

## Migrations

New migration

```bash
alembic revision -m "create XXX table"
```

> [!NOTE]  
> Run below commands inside a docker container

Check current revision

```bash
docker exec -it substio_app .venv/bin/alembic current
```

To run all of your outstanding migrations, execute the `upgrade head` command

```bash
docker exec -it substio_app .venv/bin/alembic upgrade head
```

To roll back the latest migration operation, you may use the `alembic downgrade` command

```bash
docker exec -it substio_app .venv/bin/alembic downgrade -1
```

To run rolled back migration again:

```bash
docker exec -it substio_app .venv/bin/alembic upgrade +1
```

Revision History: Use `.venv/bin/alembic history` to see the history of migrations and understand the steps involved.
Detailed View: Use `.venv/bin/alembic show <revision>` to get detailed information about specific revision scripts.

## Update python dependencies

```bash
uv lock --upgrade
```

clean cache

```bash
uv cache clean
```

### Check & format project

```bash
ruff check app/
```

```bash
ruff check app/ --fix
```

## Cold start

- alembic migration
- insert geo data `uv run locations.py`

### Truncate PG data

```postgresql
TRUNCATE TABLE cities RESTART IDENTITY CASCADE;
```

### LLM friendly version

```bash
bunx repomix --style markdown --ignore "**/*.log,tmp/,Readme.md,uv.lock"
```

```bash
`tree -P '*.py' -I '__pycache__|*.pyc' --dirsfirst`
```

### Truncate PG data

```postgresql
TRUNCATE TABLE places RESTART IDENTITY CASCADE ;
```

## LLM prices
```bash
uvx genai-prices list
```

```bash
uvx genai-prices calc --input-tokens 100000 --output-tokens 3000 GPT-5-nano GPT-4.1-nano GPT-5 claude-sonnet-4-0 claude-sonnet-4-5
```