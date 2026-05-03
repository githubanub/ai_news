from app.graphs.news_state import NewsPipelineState
from app.config import settings
from app.db import db_session
from app.integrations.serpapi_client import SerpApiClient
from app.integrations.tavily_client import TavilyClient
from app.repositories import filter_new_sources
from app.services.search_query_planner import clean_search_topic, plan_search_queries


def source_discovery_node(state: NewsPipelineState) -> NewsPipelineState:
    topic = clean_search_topic(state.get("topic", ""))
    if not topic:
        state.setdefault("errors", []).append({"node": "source_discovery", "message": "Missing topic"})
        state["discovered_sources"] = []
        return state

    tavily_api_key = settings.tavily_api_key or settings.tavilty_api_key
    if not settings.serpapi_api_key and not tavily_api_key:
        state.setdefault("errors", []).append({"node": "source_discovery", "message": "No search provider configured"})
        state["discovered_sources"] = []
        return state

    max_results = int(state.get("max_stories") or settings.max_stories_per_run)
    per_query_limit = min(max(max_results * 3, max_results), 20)
    source_pool_limit = max(80, max_results * 10)
    time_window_hours = int(state.get("time_window_hours") or settings.default_time_window_hours)
    discovered_sources: list[dict] = []
    try:
        query_plan = plan_search_queries(topic)
    except Exception as exc:
        state.setdefault("errors", []).append({"node": "source_discovery", "provider": "llm_query_planner", "message": _sanitize_error(str(exc))})
        query_plan = {"news_queries": [topic], "article_queries": [f"{topic} analysis"]}
    state["search_queries"] = query_plan

    if tavily_api_key:
        tavily_client = TavilyClient(tavily_api_key)
        try:
            for query in query_plan["article_queries"]:
                discovered_sources.extend(tavily_client.search_articles(query, max_results=per_query_limit))
        except Exception as exc:
            state.setdefault("errors", []).append({"node": "source_discovery", "provider": "tavily_articles", "message": _sanitize_error(str(exc))})
        try:
            for query in query_plan["news_queries"]:
                discovered_sources.extend(tavily_client.search_news(query, max_results=per_query_limit, time_window_hours=time_window_hours))
        except Exception as exc:
            state.setdefault("errors", []).append({"node": "source_discovery", "provider": "tavily_news", "message": _sanitize_error(str(exc))})

    if settings.serpapi_api_key:
        serpapi_client = SerpApiClient(settings.serpapi_api_key)
        try:
            for query in query_plan["article_queries"]:
                discovered_sources.extend(serpapi_client.search_google(query, max_results=per_query_limit))
        except Exception as exc:
            state.setdefault("errors", []).append({"node": "source_discovery", "provider": "serpapi_google", "message": _sanitize_error(str(exc))})
        try:
            for query in query_plan["news_queries"]:
                discovered_sources.extend(serpapi_client.search_google_news(query, max_results=per_query_limit))
        except Exception as exc:
            state.setdefault("errors", []).append({"node": "source_discovery", "provider": "serpapi_google_news", "message": _sanitize_error(str(exc))})

    deduped_sources = _dedupe_sources(discovered_sources)
    if state.get("skip_duplicate_check", False):
        new_sources = deduped_sources
    else:
        with db_session() as session:
            new_sources = filter_new_sources(session, deduped_sources)
    skipped_count = len(deduped_sources) - len(new_sources)
    state["duplicate_sources_skipped"] = skipped_count
    if skipped_count:
        state.setdefault("audit_events", []).append({"node": "source_discovery", "message": f"Skipped {skipped_count} duplicate sources"})
    state["discovered_sources"] = new_sources[:source_pool_limit]
    return state


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen_urls: set[str] = set()
    deduped: list[dict] = []
    for source in sources:
        url = source.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(source)
    return deduped


def _sanitize_error(message: str) -> str:
    if "api_key=" not in message:
        return message
    prefix, _, suffix = message.partition("api_key=")
    for separator in ("&", "'", '"', " "):
        if separator in suffix:
            _, separator, remainder = suffix.partition(separator)
            return f"{prefix}api_key=<redacted>{separator}{remainder}"
    return f"{prefix}api_key=<redacted>"
