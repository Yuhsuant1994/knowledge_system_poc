from langgraph.graph import END, StateGraph

from api.agents import github_agent, hr_rag_agent, sales_sql_agent
from api.agents.domains import DOMAIN_LABELS
from api.agents.llm import get_llm
from api.agents.state import ChatState

CLASSIFY_PROMPT = """Classify the question into exactly one category:
- hr_rag: HR / company handbook questions (culture, communication, process)
- sales_sql: questions about sales, orders, customers, products, revenue
- github: questions about the GitHub repository (issues, PRs, commits, code, CI)
- unsure: the question doesn't clearly fit any category above, or is unclear

Allowed categories for this user: {allowed}

Question: {question}

Don't force it into a category you're not confident about -- reply "unsure"
instead of guessing.

Reply in exactly this format, nothing else:
<category>: <one short sentence reason>"""

# TODO: future enhancement better maintain like a intent table
KEYWORDS = {
    "sales_sql": {
        "order",
        "orders",
        "sale",
        "sales",
        "revenue",
        "customer",
        "customers",
        "product",
        "products",
        "invoice",
        "supplier",
    },
    "github": {
        "commit",
        "commits",
        "pr",
        "pull request",
        "issue",
        "issues",
        "repo",
        "repository",
        "deploy",
        "release",
        "ci",
        "pipeline",
        "codebase",
        "source code",
        "regression",
        "click-through",
        "click through rate",
        "recommendation system",
        "recommendation engine",
        "changes in the code",
        "code change",
    },
    "hr_rag": {
        "culture",
        "handbook",
        "policy",
        "pto",
        "leave",
        "benefit",
        "remote",
        "offsite",
        "onboarding",
        "feedback",
    },
}

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


def _keyword_domain(question: str) -> str | None:
    lowered = question.lower()
    hits = {
        domain for domain, words in KEYWORDS.items() if any(w in lowered for w in words)
    }
    return next(iter(hits)) if len(hits) == 1 else None


def classify(state: ChatState) -> ChatState:
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

    keyword_domain = _keyword_domain(state["message"])
    if keyword_domain:
        if keyword_domain in allowed:
            return {
                **state,
                "route": keyword_domain,
                "reason": f"matched a {keyword_domain} keyword",
            }
        return {
            **state,
            "route": "none",
            "reason": f"matched a {keyword_domain} keyword",
            "denied_domain": keyword_domain,
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
    result = hr_rag_agent.answer(state["message"])
    return {**state, "answer": result["answer"], "sources": result["sources"]}


def route_sales(state: ChatState) -> ChatState:
    result = sales_sql_agent.answer(state["message"])
    return {
        **state,
        "answer": result["answer"],
        "sql": result.get("sql") or None,
        "sources": [],
    }


async def route_github(state: ChatState) -> ChatState:
    result = await github_agent.answer(state["message"])
    return {**state, "answer": result["answer"], "sources": result["sources"]}


def route_none(state: ChatState) -> ChatState:
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
    return state["route"]


def build_graph():
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
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
