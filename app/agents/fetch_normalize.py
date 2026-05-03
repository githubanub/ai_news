from app.graphs.news_state import NewsPipelineState
from app.integrations.article_fetcher import ArticleFetcher


def fetch_normalize_node(state: NewsPipelineState) -> NewsPipelineState:
    discovered_sources = state.get("discovered_sources", [])
    fetcher = ArticleFetcher()
    state["raw_articles"] = discovered_sources
    normalized_articles = []
    for source in discovered_sources:
        article_text = None
        if source.get("url"):
            try:
                article_text = fetcher.fetch_text(source["url"])
            except Exception as exc:
                state.setdefault("audit_events", []).append({"node": "fetch_normalize", "url": source.get("url"), "message": str(exc)})
        normalized_articles.append(
            {
                "title": source.get("title"),
                "url": source.get("url"),
                "source_name": source.get("source_name"),
                "published_at": source.get("published_at"),
                "summary": source.get("snippet"),
                "snippet": source.get("snippet"),
                "article_text": article_text,
                "provider": source.get("provider"),
                "thumbnail_url": source.get("thumbnail_url"),
            }
        )
    state["normalized_articles"] = normalized_articles
    return state
