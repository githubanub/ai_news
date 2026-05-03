from app.graphs.news_state import NewsPipelineState


def image_selection_node(state: NewsPipelineState) -> NewsPipelineState:
    state["images"] = [
        {
            "url": article["thumbnail_url"],
            "source_url": article.get("url"),
            "source_name": article.get("source_name"),
        }
        for article in state.get("selected_candidates", [])
        if article.get("thumbnail_url")
    ]
    return state
