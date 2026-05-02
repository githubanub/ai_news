from app.graphs.news_state import NewsPipelineState


def slack_approval_node(state: NewsPipelineState) -> NewsPipelineState:
    return state
