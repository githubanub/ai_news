from app.graphs.news_state import NewsPipelineState


def compliance_review_node(state: NewsPipelineState) -> NewsPipelineState:
    citations = state.get("citations", [])
    selected_candidates = state.get("selected_candidates", [])
    issues = []
    if selected_candidates and not citations:
        issues.append("Selected candidates are missing citations")
    if not selected_candidates:
        issues.append("No selected candidate stories")

    state["compliance_report"] = {
        "status": "needs_review" if issues else "ready_for_human_review",
        "issues": issues,
        "citation_count": len(citations),
    }
    return state
