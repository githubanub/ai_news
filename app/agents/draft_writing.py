from app.config import settings
from app.graphs.news_state import NewsPipelineState
from app.integrations.llm_client import LLMClient
from app.services.draft_formatter import clean_draft_text
from app.services.search_query_planner import clean_search_topic


def draft_writing_node(state: NewsPipelineState) -> NewsPipelineState:
    candidates = state.get("selected_candidates", [])
    topic = clean_search_topic(state.get("topic", "AI news"))
    if not candidates:
        state["generated_summary"] = f"No candidate stories found for {topic}."
        state["technical_blog_draft"] = {
            "title": f"No stories found: {topic}",
            "body": state["generated_summary"],
            "citations": [],
        }
        return state

    lead = candidates[0]
    if settings.llm_enabled:
        try:
            draft = _generate_llm_draft(topic, candidates, state.get("citations", []))
            state["generated_summary"] = f"Found {len(candidates)} candidate stories for {topic}. Lead: {lead.get('title')}"
            state["technical_blog_draft"] = draft
            return state
        except Exception as exc:
            state.setdefault("errors", []).append({"node": "draft_writing", "provider": "llm", "message": str(exc)})

    state["generated_summary"] = f"Found {len(candidates)} candidate stories for {topic}. Lead: {lead.get('title')}"
    state["technical_blog_draft"] = _generate_template_draft(topic, candidates, state.get("citations", []))
    return state


def _generate_template_draft(topic: str, candidates: list[dict], citations: list[dict]) -> dict:
    lead = candidates[0]
    citation_lines = [
        f"- {article.get('title')} ({article.get('source_name') or 'source'}): {article.get('url')}"
        for article in candidates[:5]
    ]
    body = "\n".join(
        [
            f"{topic}: what leaders should understand now",
            "",
            f"The signal: {lead.get('title')}",
            "",
            "What the topic is about:",
            f"{topic} is becoming a board-level operating question, not just a technology headline. The latest coverage suggests leaders should evaluate how capability, risk, governance, and accountability are moving together.",
            "",
            "Why it matters:",
            "The practical issue is no longer whether AI will affect the industry. It is whether organizations can adopt AI systems with enough control, evidence, and governance discipline to earn trust from customers, regulators, employees, and partners.",
            "",
            "Industry impact:",
            "- Compliance teams will need stronger documentation of AI use cases, vendors, controls, and human oversight.",
            "- Product and engineering teams will need to design auditability into AI workflows from the start.",
            "- Executives should expect AI risk to become part of procurement, security review, legal review, and customer assurance.",
            "- Companies that can prove responsible deployment may move faster than competitors that treat governance as a blocker.",
            "",
            "Expert take:",
            "The winning posture is not AI maximalism or AI avoidance. It is governed acceleration: move quickly where the risk is understood, slow down where decisions affect rights, safety, privacy, financial outcomes, or regulated obligations, and maintain evidence for every important assumption.",
            "",
            "Candidate source coverage:",
            *citation_lines,
            "",
            "LinkedIn-ready takeaway:",
            "The next advantage in AI will belong to organizations that can combine innovation velocity with governance maturity. The companies that operationalize controls, monitoring, and accountability now will be better positioned when regulation, enterprise buyers, and public expectations catch up.",
        ]
    )
    return {
        "title": _build_editorial_title(topic),
        "body": body,
        "citations": citations,
        "source_count": len(candidates),
        "generated_by": "template",
    }


def _generate_llm_draft(topic: str, candidates: list[dict], citations: list[dict]) -> dict:
    api_key = settings.llm_api_key or settings.openai_api_key or ""
    client = LLMClient(
        api_key=api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    source_context = "\n".join(
        [
            f"{index}. Title: {article.get('title')}\n"
            f"   Source: {article.get('source_name') or 'Unknown'}\n"
            f"   URL: {article.get('url')}\n"
            f"   Snippet: {article.get('snippet') or article.get('summary') or ''}\n"
            f"   Article text excerpt: {(article.get('article_text') or '')[:3500]}"
            for index, article in enumerate(candidates[:6], start=1)
        ]
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert AI governance, compliance, and enterprise technology analyst. "
                "Write strictly professional analysis. Do not produce illicit, unsafe, offensive, or non-professional content. "
                "Use only the provided source context. Do not invent facts, numbers, quotes, or claims. "
                "Do not copy long passages from sources. Keep the style suitable for LinkedIn: crisp, insightful, executive, and grounded."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Topic: {topic}\n\n"
                f"Sources:\n{source_context}\n\n"
                "Generate a LinkedIn-style article draft with these sections:\n"
                "1. Strong hook\n"
                "2. What changed or what the sources are signaling\n"
                "3. Why it matters now\n"
                "4. Industry impact\n"
                "5. Expert take\n"
                "6. What leaders should do next\n"
                "7. Sources used with links\n\n"
                "Requirements:\n"
                "- Sound like a charismatic senior expert, not marketing copy.\n"
                "- Be knowledgeable, concise, and insight-dense.\n"
                "- Optimize for LinkedIn traction without hype or clickbait.\n"
                "- Keep all claims tied to the provided sources.\n"
                "- Mention uncertainty where sources are only directional.\n"
                "- Do not provide legal advice."
            ),
        },
    ]
    body = clean_draft_text(client.chat(messages))
    return {
        "title": _build_editorial_title(topic),
        "body": body,
        "citations": citations,
        "source_count": len(candidates),
        "generated_by": f"llm:{settings.llm_model}",
    }


def _build_editorial_title(topic: str) -> str:
    cleaned = clean_search_topic(topic)
    normalized = " ".join(cleaned.split())
    if not normalized:
        return "AI Governance: What Leaders Need to Know Now"
    title_topic = normalized[:1].upper() + normalized[1:]
    if title_topic.lower().startswith("ai "):
        title_topic = "AI " + title_topic[3:]
    return f"{title_topic}: What Leaders Need to Know Now"
