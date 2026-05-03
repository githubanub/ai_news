# Agentic AI News Intelligence System

An agentic editorial pipeline for discovering AI, GenAI, governance, compliance, startup, and enterprise technology news; evaluating candidate sources; generating citation-grounded LinkedIn-style drafts; and routing drafts through human approval before creating downstream publishing drafts.

The system is designed around source-grounded generation, human-in-the-loop review, and auditable agent execution.

## Technical Stack

- **Language:** Python 3.11+
- **API framework:** FastAPI
- **Agent orchestration:** LangGraph `StateGraph`
- **Data validation/configuration:** Pydantic v2 and `pydantic-settings`
- **Persistence:** SQLAlchemy 2.x with a configurable `DATABASE_URL`
- **Async/background entry points:** FastAPI background tasks and scheduler support
- **HTTP clients:** `httpx`
- **Content extraction/parsing:** BeautifulSoup
- **Search integrations:** Tavily and SerpAPI
- **Human approval:** Slack webhooks, slash commands, app mentions, and interactive approval actions
- **Draft destination integration:** Webflow draft creation through a dedicated integration layer
- **Testing:** pytest and pytest-asyncio
- **Linting:** Ruff
- **Packaging/dependency management:** `pyproject.toml` with uv-compatible lockfile

## LLM Layer

LLM calls are routed through `app/integrations/llm_client.py`, a lightweight OpenAI-compatible chat completions client.

The model provider is configurable through environment variables:

- `LLM_ENABLED`: enables LLM-backed query planning and draft generation when true
- `LLM_API_KEY` or `OPENAI_API_KEY`: API key used for chat completions
- `LLM_BASE_URL`: OpenAI-compatible API base URL, defaulting to `https://api.openai.com/v1`
- `LLM_MODEL`: chat model name, defaulting to `gpt-4o-mini`
- `LLM_TIMEOUT_SECONDS`: request timeout for model calls

The client posts to `/chat/completions` with standard chat messages, temperature, and token limits. It also strips reasoning tags such as `<think>` and `<thought>` from model output before downstream use.

LLM usage appears in two places:

1. **Search query planning** in `app/services/search_query_planner.py`
   - Converts a user topic into targeted news and article search queries.
   - Uses strict JSON output.
   - Falls back to deterministic query templates when LLM mode is disabled or unavailable.

2. **Draft writing** in `app/agents/draft_writing.py`
   - Generates a professional, LinkedIn-style article draft from selected source context.
   - Instructs the model to use only provided source material.
   - Falls back to a deterministic template draft if LLM generation is disabled or fails.

## Agentic Architecture

The pipeline is implemented as a LangGraph graph in `app/graphs/news_graph.py`. Shared state is defined in `app/graphs/news_state.py` as `NewsPipelineState`.

Current graph flow:

```text
source_discovery
  -> fetch_normalize
  -> deduplication
  -> relevance_scoring
  -> claim_extraction
  -> quote_preservation
  -> citation_validation
  -> image_selection
  -> draft_writing
  -> compliance_review
  -> slack_approval
  -> END
```

Each graph node is implemented as an agent module under `app/agents/`. Nodes receive the shared state dictionary, add their own outputs, append errors or audit events when needed, and pass the updated state forward.

## Agents

- **Source discovery:** Plans searches and gathers candidate URLs from Tavily and SerpAPI.
- **Fetch and normalize:** Fetches discovered articles and normalizes article text, metadata, and source fields.
- **Deduplication:** Removes repeated or already-seen source material.
- **Relevance scoring:** Scores candidates against the requested AI/news topic and filters by `MIN_RELEVANCE_SCORE`.
- **Claim extraction:** Extracts factual claims that need citation support.
- **Quote preservation:** Tracks direct quotes separately so they can be preserved accurately.
- **Citation validation:** Maps factual claims and draft evidence back to sources.
- **Image selection:** Suggests image candidates for the selected story.
- **Draft writing:** Produces the technical/editorial draft using either the configured LLM or a deterministic template fallback.
- **Compliance review:** Checks draft quality and editorial safety before approval routing.
- **Slack approval:** Posts draft approval messages to Slack with approve, needs-edit, and reject actions.
- **Webflow publisher:** Creates a draft item only after an approval path calls it.
- **Audit logger:** Records major workflow events for traceability.

## Human-In-The-Loop Workflow

Slack is the review surface for editors and operators.

Supported Slack interactions include:

- Slash commands for topic management and news fetches
- App mentions with natural language requests
- Interactive article approval actions
- Signature verification for Slack request authenticity
- Processing locks to avoid duplicate in-flight requests from the same user/channel

Approval decisions are persisted through repository functions so downstream actions can be tied to a run, article, reviewer, and Slack message.

## Editorial Guardrails

The system includes guardrails for professional AI-news use cases:

- Topics are restricted to AI, governance, compliance, risk, privacy, security, regulation, healthcare AI, fintech, enterprise AI, startup, funding, and related professional domains.
- Disallowed topics such as malware, credential theft, phishing, scams, explicit content, drugs, and other unsafe requests are rejected.
- Draft prompts instruct the LLM to avoid invented facts, numbers, quotes, and unsupported claims.
- Draft generation uses provided source context only.
- Direct quotes are tracked separately.
- Compliance review runs before Slack approval.

## API Surface

FastAPI routers are registered in `app/main.py`.

- `GET /health`
- `POST /jobs/run-news-pipeline`
- `POST /webhooks/slack/actions`
- `POST /webhooks/slack/commands`
- `POST /webhooks/slack/events`
- Article routes under `/articles`
- Draft destination routes under `/webflow`

The main pipeline entry point is:

```http
POST /jobs/run-news-pipeline
```

Example request:

```json
{
  "topic": "AI startup funding",
  "time_window_hours": 24,
  "max_stories": 10,
  "skip_duplicate_check": true
}
```

## Configuration

Core environment variables:

```text
DATABASE_URL=
REDIS_URL=

LLM_ENABLED=false
LLM_API_KEY=
OPENAI_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=60

SERPAPI_API_KEY=
TAVILY_API_KEY=

SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_APPROVAL_CHANNEL_ID=

WEBFLOW_API_TOKEN=
WEBFLOW_SITE_ID=
WEBFLOW_COLLECTION_ID=

DEFAULT_TIME_WINDOW_HOURS=24
MAX_STORIES_PER_RUN=10
MIN_RELEVANCE_SCORE=0.72
SCHEDULER_ENABLED=false
```

## Local Development

Install dependencies:

```bash
uv sync
```

Run the API:

```bash
uv run uvicorn app.main:app --reload
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

## Repository Layout

```text
app/
  agents/          LangGraph node implementations
  api/             FastAPI routers
  graphs/          LangGraph graph and state definition
  integrations/    External service clients
  services/        Shared domain services and guardrails
  config.py        Environment-backed settings
  db.py            Database setup/session helpers
  models.py        SQLAlchemy models
  repositories.py  Persistence operations
tests/             Unit and smoke tests
```
