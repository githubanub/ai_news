from app.graphs.news_state import NewsPipelineState
from app.config import settings


GENERIC_TERMS = {
    "ai",
    "artificial",
    "intelligence",
    "news",
    "latest",
    "new",
    "update",
    "updates",
    "today",
    "due",
    "because",
    "from",
    "what",
    "opinion",
    "opinions",
    "software",
    "softwares",
    "medical",
    "applied",
    "apply",
    "used",
    "use",
    "using",
    "to",
    "in",
    "and",
    "or",
    "the",
    "a",
    "an",
    "of",
    "on",
    "for",
    "by",
    "at",
}

TERM_ALIASES = {
    "regulation": ("regulation", "regulations", "regulatory", "guidance", "policy", "rules", "rule"),
    "regulations": ("regulation", "regulations", "regulatory", "guidance", "policy", "rules", "rule"),
    "regulatory": ("regulation", "regulations", "regulatory", "guidance", "policy", "rules", "rule"),
    "software": ("software", "samd", "device", "devices"),
    "device": ("device", "devices", "software", "samd"),
    "devices": ("device", "devices", "software", "samd"),
    "hospital": ("hospital", "hospitals", "healthcare", "clinical", "health"),
    "hospitals": ("hospital", "hospitals", "healthcare", "clinical", "health"),
    "health": ("health", "healthcare", "clinical", "medical", "hospital", "hospitals"),
    "centers": ("centers", "center", "hospitals", "healthcare", "clinical"),
    "ai": ("ai", "artificial intelligence", "machine learning", "ml", "algorithm", "algorithms"),
    "job": ("job", "jobs", "workforce", "workers", "roles", "employees", "employment", "labor", "labour"),
    "jobs": ("job", "jobs", "workforce", "workers", "roles", "employees", "employment", "labor", "labour"),
    "cuts": ("cuts", "cut", "layoff", "layoffs", "laying off", "job cuts", "reduction", "reductions", "downsizing", "headcount"),
    "layoffs": ("cuts", "cut", "layoff", "layoffs", "laying off", "job cuts", "reduction", "reductions", "downsizing", "headcount"),
}


def relevance_scoring_node(state: NewsPipelineState) -> NewsPipelineState:
    topic = state.get("topic", "")
    topic_terms = _topic_terms(topic)
    strong_topic_terms = [term for term in topic_terms if term not in GENERIC_TERMS]
    scored_articles = []
    for article in state.get("deduped_articles", []):
        searchable_text = " ".join(
            str(article.get(key) or "")
            for key in ("title", "summary", "snippet", "source_name")
        )
        normalized_text = _normalize(searchable_text)
        score = _score_relevance(topic=topic, topic_terms=topic_terms, strong_topic_terms=strong_topic_terms, normalized_text=normalized_text)
        scored_articles.append({**article, "relevance_score": round(score, 2)})

    scored_articles.sort(key=lambda item: item.get("relevance_score", 0), reverse=True)
    selected_candidates = [
        article
        for article in scored_articles
        if article.get("relevance_score", 0) >= settings.min_relevance_score
    ][: int(state.get("max_stories") or settings.max_stories_per_run)]
    filtered_count = len(scored_articles) - len(selected_candidates)
    if filtered_count:
        state.setdefault("audit_events", []).append(
            {
                "node": "relevance_scoring",
                "message": f"Filtered {filtered_count} low-relevance candidates",
                "min_relevance_score": settings.min_relevance_score,
            }
        )
    state["selected_candidates"] = selected_candidates
    if selected_candidates:
        state["selected_story"] = selected_candidates[0]
    return state


def _topic_terms(topic: str) -> list[str]:
    return [term for term in _normalize(topic).replace("softwares", "software").split() if len(term) > 1]


def _normalize(text: str) -> str:
    return " ".join("".join(char.lower() if char.isalnum() else " " for char in text).split())


def _score_relevance(topic: str, topic_terms: list[str], strong_topic_terms: list[str], normalized_text: str) -> float:
    normalized_topic = _normalize(topic)
    if normalized_topic and normalized_topic in normalized_text:
        return 1.0

    if strong_topic_terms:
        strong_hits = sum(1 for term in strong_topic_terms if _term_matches(term, normalized_text))
        strong_ratio = strong_hits / len(strong_topic_terms)
        if strong_hits == 0:
            return 0.15
        score = 0.25 + (strong_ratio * 0.65)
    else:
        topic_hits = sum(1 for term in topic_terms if _term_matches(term, normalized_text))
        score = 0.2 + ((topic_hits / max(len(topic_terms), 1)) * 0.7)

    if any(term in normalized_text for term in ("funding", "raises", "raised", "startup", "launches", "announces")):
        score += 0.05
    if any(term in normalized_text for term in ("ai", "agent", "agents", "genai", "model", "llm")):
        score += 0.05
    return min(score, 1.0)


def _term_matches(term: str, normalized_text: str) -> bool:
    aliases = TERM_ALIASES.get(term, (term,))
    return any(alias in normalized_text for alias in aliases)
