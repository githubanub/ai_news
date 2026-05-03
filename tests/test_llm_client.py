from app.integrations.llm_client import _strip_reasoning


def test_strip_reasoning_removes_thought_blocks():
    assert _strip_reasoning("<thought>hidden</thought>ok") == "ok"
    assert _strip_reasoning("<think>hidden</think>{\"ok\":true}") == '{"ok":true}'
