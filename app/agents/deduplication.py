from app.graphs.news_state import NewsPipelineState


def deduplication_node(state: NewsPipelineState) -> NewsPipelineState:
    return state
