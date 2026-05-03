from bs4 import BeautifulSoup
import httpx


class ArticleFetcher:
    def fetch_text(self, url: str, max_chars: int = 5000) -> str | None:
        headers = {"User-Agent": "AI-News-System/0.1 (+https://example.com)"}
        with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type:
                return None

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
            tag.decompose()
        text_parts = [
            element.get_text(" ", strip=True)
            for element in soup.find_all(["h1", "h2", "h3", "p", "li"])
        ]
        text = " ".join(part for part in text_parts if part)
        return " ".join(text.split())[:max_chars] or None
