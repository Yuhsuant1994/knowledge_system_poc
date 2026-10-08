from langgraph.graph import END, StateGraph

from api.agents import github_agent, hr_rag_agent, sales_sql_agent
from api.agents.domains import DOMAIN_LABELS
from api.agents.llm import get_llm
from api.agents.state import ChatState

CLASSIFY_PROMPT = """Classify the question into exactly one category. If unsure, pick "unsure".

- hr_rag: HR company handbook info only (culture, policy, onboarding, benefits, offsites)
- sales_sql: this company's own sales database only (orders, revenue, customers, products, suppliers)
- github: commits/PRs/code changes in the coroot/coroot repo only
- unsure: anything else, or if not confident

Allowed categories for this user: {allowed}

Question: {question}

Reply in exactly this format, nothing else:
<category>: <one short sentence reason>"""

UNCERTAIN_MARKERS = (
    "unclear",
    "not sure",
    "unsure",
    "ambiguous",
    "doesn't specify",
    "don't know",
    "no indication",
    "not familiar",
)


def classify(state: ChatState) -> ChatState:
    """Decide which agent domain should handle the incoming message.

    Short-circuits when the role has zero or one allowed domains, otherwise
    classifies via the LLM. Denies routing to domains outside the caller's
    allowed set.

    Args:
        state: Current chat state; reads "allowed_domains" and "message".

    Returns:
        The state updated with "route" (a domain name or "none"), "reason",
        and optionally "denied_domain" if the LLM's match was blocked by
        permissions.
    """
    allowed = state["allowed_domains"]
    # Permission check
    if not allowed:
        return {
            **state,
            "route": "none",
            "reason": "this role has no agents to route to",
        }
    if len(allowed) == 1:
        route = next(iter(allowed))
        return {
            **state,
            "route": route,
            "reason": f"only {route} is accessible for this role",
        }

    raw = (
        get_llm()
        .invoke(
            CLASSIFY_PROMPT.format(
                allowed=", ".join(sorted(allowed)), question=state["message"]
            )
        )
        .content.strip()
    )
    category, _, reason = raw.partition(":")
    category = category.strip().lower()
    reason = reason.strip() or "model gave no reason"

    if category == "unsure" or any(m in reason.lower() for m in UNCERTAIN_MARKERS):
        return {**state, "route": "none", "reason": reason}
    if category in allowed:
        return {**state, "route": category, "reason": reason}
    if category in DOMAIN_LABELS:
        return {**state, "route": "none", "reason": reason, "denied_domain": category}
    return {
        **state,
        "route": "none",
        "reason": f"couldn't confidently classify this question ({raw})",
    }


def route_hr(state: ChatState) -> ChatState:
    """Graph node that delegates to the HR RAG agent.

    Args:
        state: Current chat state; reads "message".

    Returns:
        The state updated with "answer" and "sources" from the HR agent.
    """
    result = hr_rag_agent.answer(state["message"])
    return {**state, "answer": result["answer"], "sources": result["sources"]}


def route_sales(state: ChatState) -> ChatState:
    """Graph node that delegates to the sales SQL agent.

    Args:
        state: Current chat state; reads "message".

    Returns:
        The state updated with "answer", the generated "sql" (or None), and
        an empty "sources" list.
    """
    result = sales_sql_agent.answer(state["message"])
    return {
        **state,
        "answer": result["answer"],
        "sql": result.get("sql") or None,
        "sources": [],
    }


async def route_github(state: ChatState) -> ChatState:
    """Graph node that delegates to the GitHub agent.

    Args:
        state: Current chat state; reads "message".

    Returns:
        The state updated with "answer" and "sources" from the GitHub agent.
    """
    result = await github_agent.answer(state["message"])
    return {**state, "answer": result["answer"], "sources": result["sources"]}


def route_none(state: ChatState) -> ChatState:
    """Graph node that produces a fallback answer when no domain was chosen.

    Explains either that access was denied to a specific domain, that the
    role has no accessible agents at all, or that classification failed.

    Args:
        state: Current chat state; reads "denied_domain" and "allowed_domains".

    Returns:
        The state updated with an explanatory "answer" and empty "sources".
    """
    denied = state.get("denied_domain")
    if denied:
        label = DOMAIN_LABELS.get(denied, denied)
        answer = f"You don't have permission to access {label}. Please contact an admin if you need this."
    elif not state["allowed_domains"]:
        answer = "Your account has no agent access configured. Please contact an admin."
    else:
        answer = (
            "Couldn't confidently match this question to an agent you have access to."
        )
    return {**state, "answer": answer, "sources": []}


def _branch(state: ChatState) -> str:
    """Select the conditional-edge key for the graph based on routing.

    Args:
        state: Current chat state; reads "route".

    Returns:
        The route name to branch to.
    """
    return state["route"]


def build_graph():
    """Construct and compile the LangGraph chat routing graph.

    Wires a "classify" entry node with conditional edges to the "hr_rag",
    "sales_sql", "github", and "none" nodes, each terminating at END.

    Returns:
        The compiled LangGraph graph.
    """
    graph = StateGraph(ChatState)
    graph.add_node("classify", classify)
    graph.add_node("hr_rag", route_hr)
    graph.add_node("sales_sql", route_sales)
    graph.add_node("github", route_github)
    graph.add_node("none", route_none)

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        _branch,
        {
            "hr_rag": "hr_rag",
            "sales_sql": "sales_sql",
            "github": "github",
            "none": "none",
        },
    )
    for node in ("hr_rag", "sales_sql", "github", "none"):
        graph.add_edge(node, END)

    return graph.compile()


_graph = None


def get_graph():
    """Get the lazily-built, module-cached chat routing graph.

    Returns:
        The compiled LangGraph graph, building it on first call.
    """
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
