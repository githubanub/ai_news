import json
import re

from app.config import settings
from app.integrations.llm_client import LLMClient
from app.services.guardrails import validate_professional_ai_topic


def plan_search_queries(topic: str) -> dict[str, list[str]]:
    fallback = _fallback_queries(topic)
    if not settings.llm_enabled:
        return fallback

    is_allowed, error = validate_professional_ai_topic(topic)
    if not is_allowed:
        raise ValueError(error or "Topic rejected.")

    api_key = settings.llm_api_key or settings.openai_api_key or ""
    client = LLMClient(
        api_key=api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    response = client.chat(
        [
            {
                "role": "system",
                "content": (
                    "You plan search queries for a professional AI news intelligence system. "
                    "Only produce queries about AI, AI governance, compliance, risk, privacy, security, regulation, enterprise AI, startups, and related industry analysis. "
                    "Return strict JSON only. Do not include markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User topic: {topic}\n\n"
                    "Return JSON with this exact shape:\n"
                    "{\"news_queries\":[\"...\"],\"article_queries\":[\"...\"]}\n\n"
                    "Rules:\n"
                    "- Create 2 concise news queries and 2 concise article/analysis queries.\n"
                    "- Preserve the user's topic intent.\n"
                    "- Prefer current professional sources and analysis.\n"
                    "- Avoid unsafe, illicit, consumer gossip, sports, entertainment, or unrelated topics."
                ),
            },
        ],
        temperature=0.1,
        max_tokens=300,
    )
    planned = _parse_query_json(response)
    if not planned["news_queries"] and not planned["article_queries"]:
        return fallback
    return {
        "news_queries": planned["news_queries"][:2] or fallback["news_queries"],
        "article_queries": planned["article_queries"][:2] or fallback["article_queries"],
    }


def _fallback_queries(topic: str) -> dict[str, list[str]]:
    cleaned_topic = clean_search_topic(topic)
    return {
        "news_queries": [
            cleaned_topic,
            f"{cleaned_topic} latest news",
        ],
        "article_queries": [
            f"{cleaned_topic} analysis",
            f"{cleaned_topic} industry impact governance compliance",
        ],
    }


def clean_search_topic(topic: str) -> str:
    cleaned = topic.strip(" .?!")
    replacements = [
        (r"^(please\s+)?(fetch|get|find|search|show|pull)\s+(me\s+)?(the\s+)?latest\s+(news|article|articles|news and articles|articles and news)\s+(about|on|for)\s+", ""),
        (r"^(please\s+)?(fetch|get|find|search|show|pull)\s+(me\s+)?(news|article|articles|news and articles|articles and news)\s+(about|on|for)\s+", ""),
        (r"^what('?s| is)\s+the\s+latest\s+(update|updates|updated)\s+(about|on|for|of)\s+", ""),
        (r"^what('?s| is)\s+the\s+latest\s+(opinion|opinions|guidance|statement|statements)\s+(about|on|for|of)\s+", ""),
        (r"^latest\s+(update|updates|updated|news|articles)\s+(about|on|for|of)\s+", ""),
        (r"^(write|generate|draft)\s+(a\s+)?(linkedin\s+)?(article|post)\s+(about|on|for)\s+", ""),
    ]
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE).strip(" .?!")
    cleaned = cleaned.replace("softwares", "software")
    return cleaned


def _parse_query_json(response: str) -> dict[str, list[str]]:
    cleaned = _extract_json_object(response)
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    data = json.loads(cleaned)
    return {
        "news_queries": _clean_queries(data.get("news_queries", [])),
        "article_queries": _clean_queries(data.get("article_queries", [])),
    }


def _clean_queries(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


def _extract_json_object(response: str) -> str:
    cleaned = response.strip()
    if cleaned.startswith("```"):
        return cleaned
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned
