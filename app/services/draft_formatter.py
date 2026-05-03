import re


def clean_draft_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"<thought>.*?</thought>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"^\s*#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\*)\*(?!\s)(.*?)(?<!\s)\*(?!\*)", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r'(^|\n)>\s*', r"\1", cleaned)
    cleaned = re.sub(r'(?m)^["“”](.+?)["“”]\s*$', r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def slack_excerpt(text: str, limit: int = 2800) -> str:
    cleaned = clean_draft_text(text)
    if len(cleaned) <= limit:
        return cleaned
    cutoff = cleaned.rfind("\n\n", 0, limit)
    if cutoff < 800:
        cutoff = cleaned.rfind(". ", 0, limit)
    if cutoff < 800:
        cutoff = limit
    return cleaned[:cutoff].strip()
