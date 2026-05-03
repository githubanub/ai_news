import re


ALLOWED_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "agent",
    "agents",
    "agentic",
    "genai",
    "generative ai",
    "llm",
    "model",
    "machine learning",
    "governance",
    "compliance",
    "risk",
    "regulation",
    "regulatory",
    "policy",
    "audit",
    "security",
    "cybersecurity",
    "privacy",
    "data protection",
    "eu ai act",
    "nist",
    "iso",
    "soc 2",
    "hipaa",
    "fda",
    "medical software",
    "medical device",
    "healthcare ai",
    "clinical ai",
    "saamd",
    "software as a medical device",
    "fintech",
    "enterprise",
    "startup",
    "funding",
}

DISALLOWED_KEYWORDS = {
    "weapon",
    "explosive",
    "malware",
    "phishing",
    "ransomware",
    "credential theft",
    "steal",
    "bypass",
    "jailbreak",
    "hack into",
    "illegal",
    "fraud",
    "scam",
    "adult",
    "explicit",
    "drug",
}


def validate_professional_ai_topic(topic: str) -> tuple[bool, str | None]:
    normalized = _normalize(topic)
    if not normalized:
        return False, "Please include a topic."

    if any(keyword in normalized for keyword in DISALLOWED_KEYWORDS):
        return False, "I can only help with professional AI, AI governance, compliance, security, privacy, and industry news topics."

    if not any(keyword in normalized for keyword in ALLOWED_KEYWORDS):
        return False, "Topic rejected. Please keep searches focused on professional AI, AI governance, compliance, security, privacy, or related industry news."

    return True, None


def extract_news_topic(text: str) -> str | None:
    cleaned = text.strip()
    normalized = cleaned.casefold()
    patterns = [
        r"^(please\s+)?(fetch|get|find|search|show|pull)\s+(latest\s+)?(news|articles|news and articles|articles and news)\s+(about|on|for)\s+",
        r"^(please\s+)?(fetch|get|find|search|show|pull)\s+(me\s+)?(the\s+)?latest\s+(news|article|articles|news and articles|articles and news)\s+(about|on|for)\s+",
        r"^(please\s+)?(fetch|get|find|search|show|pull)\s+(me\s+)?(news|article|articles|news and articles|articles and news)\s+(about|on|for)\s+",
        r"^(please\s+)?(fetch|get|find|search|show|pull)\s+(news|articles|news and articles|articles and news)\s+(about|on|for)\s+",
        r"^(what'?s|what is)\s+(the\s+)?latest\s+(news|articles)?\s*(about|on|for)\s+",
        r"^(what'?s|what is)\s+(the\s+)?latest\s+(update|updates|updated)\s+(about|on|for|of)\s+",
        r"^(what'?s|what is)\s+(the\s+)?latest\s+(opinion|opinions|guidance|statement|statements)\s+(about|on|for|of)\s+",
        r"^(write|generate|draft)\s+(a\s+)?(linkedin\s+)?(article|post)\s+(about|on|for)\s+",
    ]
    for pattern in patterns:
        match = re.match(pattern, normalized)
        if match:
            return cleaned[match.end() :].strip(" .?!")

    if normalized in {"fetch news", "latest news", "fetch articles"}:
        return None

    return cleaned if len(cleaned.split()) >= 2 else None


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())
