from app.integrations.serpapi_client import SerpApiClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, *args, **kwargs):
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, url, params):
        self.params = params
        assert url == "https://serpapi.com/search.json"
        assert params["q"] == "AI startup funding"
        assert params["api_key"] == "test-key"
        if params["engine"] == "google_news":
            return FakeResponse(
                {
                    "news_results": [
                        {
                            "title": "Top AI story",
                            "link": "https://example.com/top-ai-story",
                            "source": {"name": "Example News"},
                            "iso_date": "2026-05-02T00:00:00Z",
                            "thumbnail": "https://example.com/image.jpg",
                        },
                        {
                            "title": "Related coverage",
                            "stories": [
                                {
                                    "title": "Nested AI story",
                                    "link": "https://example.com/nested-ai-story",
                                    "source": {"name": "Nested News"},
                                }
                            ],
                        },
                    ]
                }
            )
        assert params["engine"] == "google"
        return FakeResponse(
            {
                "organic_results": [
                    {
                        "title": "AI funding analysis",
                        "link": "https://example.com/ai-funding-analysis",
                        "source": "Example Blog",
                        "date": "May 2, 2026",
                        "snippet": "Analysis of AI startup funding.",
                    }
                ]
            }
        )


def test_serpapi_client_normalizes_google_news(monkeypatch):
    monkeypatch.setattr("app.integrations.serpapi_client.httpx.Client", FakeHttpClient)

    results = SerpApiClient("test-key").search_google_news("AI startup funding", max_results=2)

    assert results == [
        {
            "provider": "serpapi_google_news",
            "title": "Top AI story",
            "url": "https://example.com/top-ai-story",
            "source_name": "Example News",
            "published_at": "2026-05-02T00:00:00Z",
            "thumbnail_url": "https://example.com/image.jpg",
            "story_token": None,
            "serpapi_link": None,
        },
        {
            "provider": "serpapi_google_news",
            "title": "Nested AI story",
            "url": "https://example.com/nested-ai-story",
            "source_name": "Nested News",
            "published_at": None,
            "thumbnail_url": None,
            "story_token": None,
            "serpapi_link": None,
        },
    ]


def test_serpapi_client_normalizes_google_organic_results(monkeypatch):
    monkeypatch.setattr("app.integrations.serpapi_client.httpx.Client", FakeHttpClient)

    results = SerpApiClient("test-key").search_google("AI startup funding", max_results=2)

    assert results == [
        {
            "provider": "serpapi_google",
            "title": "AI funding analysis",
            "url": "https://example.com/ai-funding-analysis",
            "source_name": "Example Blog",
            "published_at": "May 2, 2026",
            "snippet": "Analysis of AI startup funding.",
            "thumbnail_url": None,
        }
    ]
