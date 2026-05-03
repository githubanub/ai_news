from typing import Any

import httpx


class SerpApiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search.json"

    def search_google_news(self, query: str, max_results: int) -> list[dict[str, Any]]:
        params = {
            "engine": "google_news",
            "q": query,
            "api_key": self.api_key,
            "hl": "en",
            "gl": "us",
            "so": "1",
        }
        with httpx.Client(timeout=30) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()

        if payload.get("error"):
            raise RuntimeError(str(payload["error"]))

        return self._normalize_results(payload.get("news_results", []), max_results)

    def search_google(self, query: str, max_results: int) -> list[dict[str, Any]]:
        params = {
            "engine": "google",
            "q": query,
            "api_key": self.api_key,
            "hl": "en",
            "gl": "us",
            "num": max_results,
        }
        with httpx.Client(timeout=30) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()

        if payload.get("error"):
            raise RuntimeError(str(payload["error"]))

        return self._normalize_organic_results(payload.get("organic_results", []), max_results)

    def _normalize_results(self, results: list[dict[str, Any]], max_results: int) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in results:
            self._append_result(normalized, item, max_results)
            for key in ("highlight",):
                nested = item.get(key)
                if isinstance(nested, dict):
                    self._append_result(normalized, nested, max_results)
            for story in item.get("stories", []):
                if isinstance(story, dict):
                    self._append_result(normalized, story, max_results)
            if len(normalized) >= max_results:
                break
        return normalized[:max_results]

    def _append_result(self, normalized: list[dict[str, Any]], item: dict[str, Any], max_results: int) -> None:
        if len(normalized) >= max_results:
            return
        link = item.get("link")
        title = item.get("title")
        if not link or not title:
            return

        source = item.get("source") or {}
        normalized.append(
            {
                "provider": "serpapi_google_news",
                "title": title,
                "url": link,
                "source_name": source.get("name") or source.get("title"),
                "published_at": item.get("iso_date") or item.get("date"),
                "thumbnail_url": item.get("thumbnail") or item.get("thumbnail_small"),
                "story_token": item.get("story_token"),
                "serpapi_link": item.get("serpapi_link"),
            }
        )

    def _normalize_organic_results(self, results: list[dict[str, Any]], max_results: int) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in results:
            link = item.get("link")
            title = item.get("title")
            if not link or not title:
                continue
            normalized.append(
                {
                    "provider": "serpapi_google",
                    "title": title,
                    "url": link,
                    "source_name": item.get("source"),
                    "published_at": item.get("date"),
                    "snippet": item.get("snippet"),
                    "thumbnail_url": item.get("thumbnail"),
                }
            )
            if len(normalized) >= max_results:
                break
        return normalized
