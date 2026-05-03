from app.services import search_query_planner


def test_plan_search_queries_uses_llm_when_enabled(monkeypatch):
    monkeypatch.setattr(search_query_planner.settings, "llm_enabled", True)
    monkeypatch.setattr(search_query_planner.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(search_query_planner.settings, "llm_model", "test-model")

    class FakeLLMClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def chat(self, messages, temperature, max_tokens):
            assert "EU AI Act compliance" in messages[1]["content"]
            assert temperature == 0.1
            assert max_tokens == 300
            return '{"news_queries":["EU AI Act compliance latest enforcement","AI Act compliance news"],"article_queries":["EU AI Act compliance analysis","AI governance compliance impact"]}'

    monkeypatch.setattr(search_query_planner, "LLMClient", FakeLLMClient)

    result = search_query_planner.plan_search_queries("EU AI Act compliance")

    assert result == {
        "news_queries": ["EU AI Act compliance latest enforcement", "AI Act compliance news"],
        "article_queries": ["EU AI Act compliance analysis", "AI governance compliance impact"],
    }


def test_plan_search_queries_falls_back_without_llm(monkeypatch):
    monkeypatch.setattr(search_query_planner.settings, "llm_enabled", False)

    result = search_query_planner.plan_search_queries("agentic AI risk")

    assert result["news_queries"] == ["agentic AI risk", "agentic AI risk latest news"]
    assert result["article_queries"] == ["agentic AI risk analysis", "agentic AI risk industry impact governance compliance"]


def test_clean_search_topic_removes_question_prefix_and_normalizes_software():
    assert search_query_planner.clean_search_topic("what is the latest updated on FDA opinion of AI medical softwares?") == "FDA opinion of AI medical software"
    assert search_query_planner.clean_search_topic("fetch me latest article on AI governance") == "AI governance"
    assert search_query_planner.clean_search_topic("fetch me the latest articles on Job cuts due to AI") == "Job cuts due to AI"


def test_parse_query_json_extracts_json_from_reasoning_text():
    response = '<thought>planning</thought>{"news_queries":["FDA AI medical software"],"article_queries":["FDA AI medical software analysis"]}'

    assert search_query_planner._parse_query_json(response) == {
        "news_queries": ["FDA AI medical software"],
        "article_queries": ["FDA AI medical software analysis"],
    }
