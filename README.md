# Secure AI Banking Assistant V3

Install dependencies with `uv sync`. Configure the LLM provider and API key in
`.env`, along with these local PostgreSQL settings:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=banking_db
POSTGRES_USER= 
POSTGRES_PASSWORD= 
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

Agent tools are registered in `agents/tools/registry.py`. `ALLOWED_TOOL_NAMES`
allows `calculate_simple_interest`, `get_transactions`, and `transfer_money`.
The transaction tool returns five fictional sample transactions, newest first,
with dates, descriptions, debit/credit types, amounts, and SAR currency.
Registration alone does not enable a tool: both model binding and graph execution use the
resolved allowed list. Unknown or disallowed tool calls return tool errors
without execution. Invalid allowlist entries fail during agent initialization.
Tests or application wiring can supply `tool_registry` and `allowed_tool_names`
to `BankingAgent`; an empty allowed list disables all tools.

`agents/policy.py` defines server-owned `ALLOW`, `DENY`, and `REQUIRE_APPROVAL`
rules. The Tool Execution Gateway checks every graph tool call immediately before
execution. Tools outside the allowed list, missing rules, and unknown tools are
denied. Simple interest and fictional sample transaction history default to `ALLOW`, and
`transfer_money` to `REQUIRE_APPROVAL`. Transfers are fictional simulations;
no funds move and no banking system is contacted.

### Human review

Normal agent calls enable human review. A dedicated review node uses LangGraph `interrupt()`
to pause before an approval-required tool executes. All reviews in a tool batch
finish before the tool node runs, preventing execution replay during review. Pending calls are saved in
the configured checkpointer. The chat response includes `status: "approval_required"`
and `pending_approvals`, with an approval ID, tool name, call ID, and exact arguments.
Both Streamlit entry points use the shared UI in `banking_assistant/frontend/ui.py`.
They show recipient, amount, exact arguments, Approve/Reject/Cancel buttons, and
an expiry countdown with the deadline in Asia/Riyadh time. Expired review controls
are disabled. All five review outcomes appear in the conversation history.

Use **Refresh review status** in the sidebar to retrieve the current review through
`GET /api/v1/chat/{thread_id}/approvals`. This resolves expired reviews without adding
chat messages or asking the model a new question. Timeouts, invalid responses,
and stale approval errors preserve the displayed review and disable resubmission
until status is refreshed. The UI never automatically retries an approval.
Chat text such as "I approve" cannot resume execution. New chat messages while a
review is pending return the existing review without changing the paused call.

Submit a decision to `POST /api/v1/chat/approvals`:

```json
{
  "thread_id": "your-thread-id",
  "approval_id": "approval-id-from-chat-response",
  "decision": "approve"
}
```

Use `"reject"` or `"cancel"` to skip execution. Reviews have a five-minute TTL,
configurable through `BankingAgent(approval_ttl_seconds=...)`. The deadline is
checkpointed before pausing and cannot be renewed by a restart. Expiry is resolved
on the next chat or review request; no background timer is required to block execution.
The gateway checks expiry again immediately before invoking the tool.

`review_outcomes` maps call fingerprints to `approved`, `rejected`, `expired`,
`cancelled`, or `invalid_response`. Only approved, unexpired calls may execute.
Rejected, expired, cancelled, and malformed graph responses return a deterministic
message and end the graph without asking the model to retry. In a mixed batch,
valid approved calls may execute while blocked calls are skipped. Malformed API
requests return HTTP 422 and leave the review pending so it can be corrected;
malformed graph resume payloads terminate that call as `invalid_response`.
The endpoint accepts no replacement tool arguments. Approval is bound to the
saved call fingerprint and thread. Missing or consumed IDs return HTTP 409.
Resuming uses the same checkpoint and thread, including after agent reconstruction.
A response can contain further pending reviews when several calls need approval.

Trusted application code can still pass `PolicyContext` with exact-call approval
fingerprints. Explicit contexts default to `human_review=False`, preserving the
noninteractive policy behavior; set `human_review=True` to enable interrupt review.

This is a demo review flow: the API currently has no user authentication or
reviewer authorization, so thread and approval IDs do not establish reviewer identity.
Before connecting real banking operations, add authenticated thread ownership,
reviewer authorization, and durable operation idempotency. Per-thread locks serialize
requests within one agent process; multiple workers require shared serialization.
The existing PostgreSQL checkpointer persists pauses across application restarts.

Run `uv run pytest -q tests/test_hitl.py tests/test_transfer_tool.py tests/test_streamlit_ui.py` to verify
pause/resume, approval/rejection, thread isolation, stale IDs, and input validation.

## MCP tools

The bundled stdio MCP server exposes `calculate_simple_interest`,
`get_transactions`, and `transfer_money`. It registers tools only, with no
resources or prompts. All operations reuse the existing validation and demo logic.

Set `MCP_ENABLED=true` in `.env` to use MCP-backed tools in the API's banking
agent, then start the API as usual. The default is `false` (local tools).
MCP mode also connects GitHub (requires `GITHUB_TOKEN`) and the remote weather
server at `https://open-meteo.caseyjhand.com/mcp`. Weather access is restricted
to `openmeteo_search_locations` and `openmeteo_get_forecast`; both are allowed
by the execution policy. These remote sessions close at application shutdown.
Try “What is the current weather in Riyadh, Saudi Arabia?” in Streamlit.
The agent resolves the location before fetching conditions; the Tool trace
expander shows the calls and their results' statuses. Remote connection or
discovery failures prevent MCP-mode startup.
Startup launches the server using the same Python interpreter, initializes an
MCP session, discovers the explicitly allowed tools, and binds adapters through
the existing tool registry. Missing tools fail startup. The approval gateway
still checks agent calls before they reach MCP. Shutdown closes the session
and subprocess; MCP requests have a 30-second timeout.

To run the server for another local MCP host:

```bash
uv run python -m banking_assistant.mcp.server
```

Configure the host with command `uv` and arguments
`["run", "--directory", "/absolute/path/to/secure-ai-banking-assistant-v3",
"python", "-m", "banking_assistant.mcp.server"]`.
The server uses stdout for protocol messages and stderr for logs.
Direct MCP callers are responsible for their own approval policy; the server
only offers fictional records and simulated transfers, with no real banking access.

Run `uv run pytest -q tests/test_mcp.py` for a real stdio round trip,
tool validation, allowlist checks, and tools-only capability verification.
