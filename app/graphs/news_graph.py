from langgraph.graph import END, StateGraph
from app.graphs.news_state import NewsPipelineState
from app.agents.source_discovery import source_discovery_node
from app.agents.fetch_normalize import fetch_normalize_node
from app.agents.deduplication import deduplication_node
from app.agents.relevance_scoring import relevance_scoring_node
from app.agents.claim_extraction import claim_extraction_node
from app.agents.quote_preservation import quote_preservation_node
from app.agents.citation_validation import citation_validation_node
from app.agents.image_selection import image_selection_node
from app.agents.draft_writing import draft_writing_node
from app.agents.compliance_review import compliance_review_node
from app.agents.slack_approval import slack_approval_node


def build_news_graph():
    graph = StateGraph(NewsPipelineState)
    graph.add_node("source_discovery", source_discovery_node)
    graph.add_node("fetch_normalize", fetch_normalize_node)
    graph.add_node("deduplication", deduplication_node)
    graph.add_node("relevance_scoring", relevance_scoring_node)
    graph.add_node("claim_extraction", claim_extraction_node)
    graph.add_node("quote_preservation", quote_preservation_node)
    graph.add_node("citation_validation", citation_validation_node)
    graph.add_node("image_selection", image_selection_node)
    graph.add_node("draft_writing", draft_writing_node)
    graph.add_node("compliance_review", compliance_review_node)
    graph.add_node("slack_approval", slack_approval_node)

    graph.set_entry_point("source_discovery")
    graph.add_edge("source_discovery", "fetch_normalize")
    graph.add_edge("fetch_normalize", "deduplication")
    graph.add_edge("deduplication", "relevance_scoring")
    graph.add_edge("relevance_scoring", "claim_extraction")
    graph.add_edge("claim_extraction", "quote_preservation")
    graph.add_edge("quote_preservation", "citation_validation")
    graph.add_edge("citation_validation", "image_selection")
    graph.add_edge("image_selection", "draft_writing")
    graph.add_edge("draft_writing", "compliance_review")
    graph.add_edge("compliance_review", "slack_approval")
    graph.add_edge("slack_approval", END)
    return graph.compile()


news_graph = build_news_graph()
