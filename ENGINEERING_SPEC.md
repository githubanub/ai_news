# Agentic AI News Intelligence System — Engineering Specification (Canonical)

**Version:** 1.1  
**Date:** 2026-05-02  
**Status:** Canonical

## 1) Purpose
Build a production-grade, human-in-the-loop agentic editorial system that discovers niche AI/GenAI/startup/product news, generates citation-grounded technical drafts, routes candidates to Slack for approval, and creates **Webflow drafts only** (never auto-publish).

## 2) Non-Negotiable Requirements
1. Use official/compliant sources.
2. Preserve direct quotes exactly.
3. Every factual claim must map to at least one source citation.
4. No long-copying from source text.
5. No unauthorized/private LinkedIn collection.
6. Slack approval is required before Webflow draft creation.
7. Webflow items must be created with `isDraft=true` and **must never be published automatically**.
8. All major actions must emit audit events.
9. System must be observable, retry-safe, idempotent.
10. Architecture must support more sources and publishers.

## 3) Core Pipeline
```text
Scheduled discovery
  -> fetch + normalize
  -> deduplicate
  -> relevance score
  -> claim extraction
  -> quote preservation
  -> citation validation
  -> image suggestion
  -> technical draft generation
  -> compliance review
  -> Slack approval
  -> (approved) Webflow draft creation
  -> audit logging
```

## 4) Architecture & Execution Contract
- API is request/response and **asynchronous** for pipeline execution.
- `/jobs/run-news-pipeline` enqueues work and returns immediately.
- Worker executes LangGraph, persists state/checkpoints, and pauses at human approval.
- Slack webhook resumes workflow using idempotent approval events.

```text
Scheduler -> FastAPI /jobs/run-news-pipeline -> Queue/Worker -> LangGraph
                                   |                         |
                                   v                         v
                              PostgreSQL/Redis         Slack approval
                                                             |
                                                             v
                                                      Webflow draft
```

## 5) Stack (Recommended)
- Python 3.11+, FastAPI, LangGraph, Pydantic v2
- SQLAlchemy 2.x, PostgreSQL, pgvector
- Redis
- Celery (or RQ/Dramatiq)
- Alembic
- OpenAI/Azure OpenAI/Anthropic/Bedrock
- OpenTelemetry (+ optional LangSmith)

## 6) Workflow State (Corrected)
Create `app/graphs/news_state.py`:
```python
from typing import Any, Literal, Optional, TypedDict


class NewsPipelineState(TypedDict, total=False):
    run_id: str
    state_version: int
    last_completed_node: str
    idempotency_key: str

    topic: str
    time_window_hours: int
    max_stories: int

    discovered_sources: list[dict[str, Any]]
    raw_articles: list[dict[str, Any]]
    normalized_articles: list[dict[str, Any]]
    deduped_articles: list[dict[str, Any]]
    selected_candidates: list[dict[str, Any]]

    selected_story: dict[str, Any]
    extracted_claims: list[dict[str, Any]]
    preserved_quotes: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    images: list[dict[str, Any]]

    generated_summary: str
    technical_blog_draft: dict[str, Any]
    compliance_report: dict[str, Any]

    slack_channel_id: Optional[str]
    slack_message_ts: Optional[str]
    approval_status: Literal["pending", "approved", "rejected", "needs_edit"]
    reviewer_comments: Optional[str]
    approval_event_id: Optional[str]

    webflow_publish_attempted: bool
    webflow_item_id: Optional[str]
    webflow_draft_url: Optional[str]

    audit_events: list[dict[str, Any]]
    errors: list[dict[str, Any]]
```

## 7) LangGraph Flow (Ambiguity Removed)
```text
START
 -> source_discovery
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
 -> END_PENDING_HUMAN_APPROVAL

Resume path on Slack action (webhook-triggered):
- approved   -> webflow_publisher -> audit_logger -> END
- rejected   -> audit_logger -> END
- needs_edit -> draft_writing -> compliance_review -> slack_approval -> END_PENDING_HUMAN_APPROVAL
```

### Conditional Routing Contract
`slack_approval` sets `approval_status`; resume entrypoint dispatches by that value. Unknown status => error + audit event.

## 8) API Contracts (Corrected)
### `POST /jobs/run-news-pipeline`
- Enqueue job; do not run graph inline.
- Request:
```json
{ "topic": "AI startups, GenAI products, agentic AI", "time_window_hours": 24, "max_stories": 10 }
```
- Response:
```json
{ "run_id": "uuid", "status": "queued" }
```

### `GET /jobs/{run_id}`
Returns lifecycle:
```json
{ "run_id": "uuid", "status": "queued|running|waiting_approval|completed|failed", "updated_at": "ISO-8601" }
```

### `POST /webhooks/slack/actions`
Responsibilities:
1. Verify Slack signature.
2. Enforce idempotency (`approval_event_id`).
3. Persist approval state.
4. Resume graph path.
5. Update Slack message.

### `POST /webflow/create-draft`
Internal/admin endpoint for explicit draft creation from `draft_id`.

## 9) Data Model Corrections
### `drafts` (add confidence and run linkage)
```sql
ALTER TABLE drafts
  ADD COLUMN confidence_score NUMERIC,
  ADD COLUMN run_id UUID;
```

- `confidence_score` stored in range `[0.0, 1.0]`.
- Webflow payload converts to integer percent `0..100`.

### `approvals` (idempotency)
```sql
ALTER TABLE approvals
  ADD COLUMN approval_event_id TEXT UNIQUE;
```

### `webflow_items` (no duplicates per draft)
```sql
CREATE UNIQUE INDEX uq_webflow_items_draft_id ON webflow_items(draft_id);
```

## 10) Slack Signature Verification
Use constant-time compare, 5-minute replay window, and reject missing headers.

## 11) Webflow Draft Safety Rules
- Always send `isDraft: true`, `isArchived: false`.
- Never call publish endpoint in MVP.
- Validate required field IDs/keys before sending.
- Sanitize HTML before submit.

Example payload:
```json
{
  "isArchived": false,
  "isDraft": true,
  "fieldData": {
    "name": "Post title",
    "slug": "post-title",
    "summary": "Summary",
    "body": "<h2>What happened</h2><p>...</p>",
    "approval-status": "Approved by Slack",
    "ai-confidence-score": 86
  }
}
```

## 12) Sources & Compliance
MVP sources:
- RSS, Hacker News API, Reddit API, web search API, company blogs, GitHub API, optional Product Hunt API.

LinkedIn policy:
- No scraping.
- Allow manual URL submission for editors.
- Use only approved official APIs if available.

## 13) Deduplication
Use URL/title/hash/embedding/entity overlap/time window.
```python
is_duplicate = (
    cosine_similarity > 0.88
    and entity_overlap > 0.60
    and abs((published_at_a - published_at_b).total_seconds()) < 172800
)
```
Persist duplicate linkage for explainability.

## 14) Relevance Scoring
- Score 0..1 with component scores and rationale.
- Gate Slack candidates by `MIN_RELEVANCE_SCORE`.

## 15) Editorial Integrity Controls
- Claims must be source-backed.
- No implicit funding/valuation/user/revenue claims unless explicit.
- Quotes are exact text only.
- Keep quotes short; use at most 1–2 short quotes.
- Copyright risk screening before Slack.

## 16) Retry, Idempotency, DLQ
Retryable:
- timeout, 429, 5xx, transient DB/network errors.

Non-retryable:
- invalid Slack signature, invalid Webflow mapping, compliance rejection.

Backoff: 1m -> 5m -> 15m -> 1h -> DLQ.

Idempotency keys:
- Per run start request.
- Per Slack action event.
- Per Webflow draft create attempt.

## 17) Observability
Emit structured events for each node:
```json
{ "run_id":"uuid", "node":"claim_extraction", "status":"success", "duration_ms":1320, "input_count":4, "output_count":18 }
```
Track:
- discovered stories/run
- approval rate
- rejection reasons
- citation failure rate
- quote integrity failure rate
- webflow draft success rate
- slack approval latency

## 18) Milestones (Execution Order)
1. Project scaffold + config + Docker
2. Models + Alembic (+ corrected fields/indexes)
3. Source clients (official APIs; mocked first)
4. LangGraph skeleton + state/checkpoints
5. Dedup + relevance + extraction + compliance nodes
6. Slack approval flow + idempotent webhook
7. Webflow draft creator (draft-only)
8. Tests + observability + retry hardening

## 19) Minimum Test Matrix
- Slack signature verification (valid/invalid/replay)
- Quote preservation exactness
- Claim-to-citation coverage
- Deduplication behavior
- Slack action idempotency
- Webflow payload validity (`isDraft=true`, publish never called)
- End-to-end: source -> draft -> Slack approve -> Webflow draft

## 20) System Identity
This is an AI-native editorial ops platform for high-signal technical intelligence with human governance, citation grounding, and operational safety.
