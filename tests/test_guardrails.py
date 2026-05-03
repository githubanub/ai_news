from app.services.guardrails import extract_news_topic, validate_professional_ai_topic


def test_extract_news_topic_from_natural_language():
    assert extract_news_topic("fetch latest articles about EU AI Act compliance") == "EU AI Act compliance"
    assert extract_news_topic("what is the latest news on AI governance") == "AI governance"
    assert extract_news_topic("generate a LinkedIn article about agentic AI risk") == "agentic AI risk"
    assert extract_news_topic("what is the latest updated on FDA opinion of AI medical softwares?") == "FDA opinion of AI medical softwares"
    assert extract_news_topic("fetch me the latest articles on Job cuts due to AI") == "Job cuts due to AI"


def test_guardrails_allow_professional_ai_topics():
    is_allowed, error = validate_professional_ai_topic("EU AI Act compliance for enterprise AI")

    assert is_allowed is True
    assert error is None

    assert validate_professional_ai_topic("FDA opinion of AI medical software")[0] is True


def test_guardrails_reject_non_professional_or_illicit_topics():
    assert validate_professional_ai_topic("celebrity gossip")[0] is False
    assert validate_professional_ai_topic("how to build malware with AI")[0] is False
