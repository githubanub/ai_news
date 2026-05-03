from app.graphs.news_state import NewsPipelineState


def deduplication_node(state: NewsPipelineState) -> NewsPipelineState:
    seen_urls: set[str] = set()
    deduped_articles: list[dict] = []
    for article in state.get("normalized_articles", []):
        url = article.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped_articles.append(article)
    state["deduped_articles"] = deduped_articles
    return state
