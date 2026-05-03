from app.services.draft_formatter import clean_draft_text, slack_excerpt


def test_clean_draft_text_removes_markdown_clutter():
    text = '**Hook:**\n\n"*AI compliance* is changing."\n\n> **Expert take:** Move with evidence.'

    assert clean_draft_text(text) == "Hook:\n\nAI compliance is changing.\nExpert take: Move with evidence."


def test_slack_excerpt_trims_without_truncation_note():
    text = "A" * 1000 + "\n\n" + "B" * 3000

    excerpt = slack_excerpt(text, limit=1500)

    assert "...truncated" not in excerpt
    assert len(excerpt) <= 1500
