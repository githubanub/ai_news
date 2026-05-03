from app.graphs.news_state import NewsPipelineState


def quote_preservation_node(state: NewsPipelineState) -> NewsPipelineState:
    state["preserved_quotes"] = []
    return state
