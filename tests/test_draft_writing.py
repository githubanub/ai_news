from app.agents import draft_writing


def test_draft_writing_uses_llm_when_enabled(monkeypatch):
    monkeypatch.setattr(draft_writing.settings, "llm_enabled", True)
    monkeypatch.setattr(draft_writing.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(draft_writing.settings, "llm_model", "test-model")

    class FakeLLMClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def chat(self, messages):
            assert "AI governance" in messages[1]["content"]
            return "LLM generated LinkedIn article"

    monkeypatch.setattr(draft_writing, "LLMClient", FakeLLMClient)

    state = {
        "topic": "AI governance",
        "selected_candidates": [
            {
                "title": "AI governance rules expand",
                "url": "https://example.com/ai-governance",
                "source_name": "Example News",
                "snippet": "New AI governance developments.",
            }
        ],
        "citations": [{"url": "https://example.com/ai-governance"}],
        "errors": [],
    }

    result = draft_writing.draft_writing_node(state)

    assert result["technical_blog_draft"]["body"] == "LLM generated LinkedIn article"
    assert result["technical_blog_draft"]["generated_by"] == "llm:test-model"
    assert result["technical_blog_draft"]["title"] == "AI governance: What Leaders Need to Know Now"
