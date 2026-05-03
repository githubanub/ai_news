from app.graphs.news_state import NewsPipelineState


def citation_validation_node(state: NewsPipelineState) -> NewsPipelineState:
    citations = []
    for claim in state.get("extracted_claims", []):
        if claim.get("source_url"):
            citations.append(
                {
                    "url": claim["source_url"],
                    "title": claim["claim"],
                    "source_name": claim.get("source_name"),
                }
            )
    state["citations"] = citations
    return state
