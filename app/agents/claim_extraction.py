from app.graphs.news_state import NewsPipelineState


def claim_extraction_node(state: NewsPipelineState) -> NewsPipelineState:
    claims = []
    for article in state.get("selected_candidates", [])[:5]:
        if article.get("title") and article.get("url"):
            claims.append(
                {
                    "claim": article["title"],
                    "source_url": article["url"],
                    "source_name": article.get("source_name"),
                }
            )
    state["extracted_claims"] = claims
    return state
