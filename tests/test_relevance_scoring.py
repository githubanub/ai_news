from app.agents.relevance_scoring import relevance_scoring_node


def test_relevance_scoring_filters_generic_ai_news_for_funding_topic():
    state = {
        "topic": "AI startup funding",
        "max_stories": 5,
        "deduped_articles": [
            {
                "title": "Colorado AI Act Rewrite Moves Forward",
                "snippet": "Colorado AI regulation update for employers.",
                "source_name": "Forbes",
                "url": "https://example.com/colorado-ai-act",
            },
            {
                "title": "AI startup raises seed funding for developer agents",
                "snippet": "The company raised a new funding round.",
                "source_name": "Example News",
                "url": "https://example.com/ai-startup-funding",
            },
        ],
        "audit_events": [],
    }

    result = relevance_scoring_node(state)

    assert [article["url"] for article in result["selected_candidates"]] == ["https://example.com/ai-startup-funding"]
    assert result["selected_story"]["url"] == "https://example.com/ai-startup-funding"


def test_relevance_scoring_keeps_fda_ai_medical_software_results():
    state = {
        "topic": "FDA opinion of AI medical software",
        "max_stories": 5,
        "deduped_articles": [
            {
                "title": "FDA releases guidance on AI-enabled medical device software",
                "snippet": "The agency discusses software as a medical device and AI model lifecycle expectations.",
                "source_name": "FDA",
                "url": "https://example.com/fda-ai-medical-software",
            }
        ],
        "audit_events": [],
    }

    result = relevance_scoring_node(state)

    assert result["selected_candidates"][0]["url"] == "https://example.com/fda-ai-medical-software"


def test_relevance_scoring_keeps_ai_job_cut_results():
    state = {
        "topic": "Job cuts due to AI",
        "max_stories": 5,
        "deduped_articles": [
            {
                "title": "Company announces layoffs as AI automates support roles",
                "snippet": "The workforce reduction follows a shift toward artificial intelligence tools.",
                "source_name": "Example News",
                "url": "https://example.com/ai-layoffs",
            }
        ],
        "audit_events": [],
    }

    result = relevance_scoring_node(state)

    assert result["selected_candidates"][0]["url"] == "https://example.com/ai-layoffs"
