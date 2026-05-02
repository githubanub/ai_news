from typing import Any, Literal, Optional, TypedDict


class NewsPipelineState(TypedDict, total=False):
    run_id: str
    topic: str
    time_window_hours: int
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
    webflow_item_id: Optional[str]
    webflow_draft_url: Optional[str]
    audit_events: list[dict[str, Any]]
    errors: list[dict[str, Any]]
