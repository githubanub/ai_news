from math import ceil
from typing import Any
from urllib.parse import urlparse

import httpx


class TavilyClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/search"

    def search_news(self, query: str, max_results: int, time_window_hours: int) -> list[dict[str, Any]]:
        days = max(1, ceil(time_window_hours / 24))
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "query": query,
            "topic": "news",
            "search_depth": "basic",
            "max_results": max_results,
            "days": days,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }

        with httpx.Client(timeout=30) as client:
            response = client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return [self._normalize_result(result) for result in data.get("results", [])[:max_results] if result.get("url")]

    def search_articles(self, query: str, max_results: int) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "query": query,
            "topic": "general",
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }

        with httpx.Client(timeout=30) as client:
            response = client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return [
            {**self._normalize_result(result), "provider": "tavily_general"}
            for result in data.get("results", [])[:max_results]
            if result.get("url")
        ]

    def _normalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        url = result.get("url")
        hostname = urlparse(url).netloc.removeprefix("www.") if url else None
        return {
            "provider": "tavily_news",
            "title": result.get("title") or url,
            "url": url,
            "source_name": hostname,
            "published_at": result.get("published_date") or result.get("date"),
            "snippet": result.get("content"),
            "score": result.get("score"),
            "thumbnail_url": result.get("favicon"),
        }
