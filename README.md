# Secure AI Banking Assistant V3

Install dependencies with `uv sync`. Configure the LLM provider and API key in
`.env`, along with these local PostgreSQL settings:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=banking_db
POSTGRES_USER=banking
POSTGRES_PASSWORD=admin123
```

Start the persistent local database and then the API:

```sh
docker compose up -d --wait postgres
uv run uvicorn banking_assistant.main:app --reload
```

The API opens a PostgreSQL connection pool on startup and calls LangGraph's
checkpoint setup to create and migrate `checkpoint_migrations`, `checkpoints`,
`checkpoint_blobs`, and `checkpoint_writes`. Startup fails if the database is
unavailable. Connections close on shutdown. The database user needs permission
to create tables and indexes during initialization.

Send requests to `POST /api/v1/chat` with `message` and `thread_id`. Reusing a
thread ID resumes its saved conversation, including after an API restart.
Different thread IDs have separate histories. Thread IDs are not authentication;
use trusted, user-scoped IDs before exposing stored conversations to customers.

`docker compose down` preserves the database volume. The credentials above are
for local development; configure separate credentials for deployed environments.
`.env` is excluded from version control.
