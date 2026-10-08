from api.agents.llm import get_llm

JUDGE_PROMPT = """You are grading an AI assistant's answer to a question.

Question: {question}
Answer: {answer}
Reference grounding (may be empty): {grounding}

Score the answer from 1 to 5 on each axis below:
- correctness: does the answer correctly address the question? Use the \
reference grounding as the source of truth when it's non-empty.
- groundedness: is the answer supported by the reference grounding rather \
than invented?
- relevance: does the answer stay on topic and actually respond to the question?

Reply in exactly this format, one line per metric, nothing else:
correctness: <score>: <one short sentence reason>
groundedness: <score>: <one short sentence reason>
relevance: <score>: <one short sentence reason>"""

METRICS = ("correctness", "groundedness", "relevance")


def judge(question: str, answer: str, grounding: str) -> dict:
    """Score an agent's answer on correctness, groundedness, and relevance.

    Calls the LLM once with a grading prompt and parses its reply using the
    same "label: ... " line-partitioning style as router.classify(). If
    grounding is empty, there's nothing to hallucinate against, so
    groundedness is forced to 5 regardless of what the model said.

    Args:
        question: The question that was asked.
        answer: The agent's answer to grade.
        grounding: Reference fact/context to grade against, or "" if none.

    Returns:
        A dict with int (or None) scores for "correctness", "groundedness",
        "relevance", a "reasoning" dict of per-metric one-line reasons, and
        a "parse_error" key holding the raw reply if parsing failed.
    """
    raw = (
        get_llm()
        .invoke(
            JUDGE_PROMPT.format(
                question=question, answer=answer, grounding=grounding or "(none)"
            )
        )
        .content.strip()
    )

    scores: dict[str, int | None] = {}
    reasoning: dict[str, str] = {}
    for line in raw.splitlines():
        metric, _, rest = line.partition(":")
        metric = metric.strip().lower()
        if metric not in METRICS:
            continue
        score_str, _, reason = rest.strip().partition(":")
        try:
            scores[metric] = int(score_str.strip())
        except ValueError:
            scores[metric] = None
        reasoning[metric] = reason.strip() or "model gave no reason"

    if any(metric not in scores or scores[metric] is None for metric in METRICS):
        return {
            "correctness": None,
            "groundedness": None,
            "relevance": None,
            "reasoning": reasoning,
            "parse_error": raw,
        }

    if not grounding:
        scores["groundedness"] = 5
        reasoning["groundedness"] = "no grounding provided, nothing to hallucinate against"

    return {**scores, "reasoning": reasoning}


def judge_with_external_model(question: str, answer: str, grounding: str) -> dict:
    """Placeholder for scoring with a stronger, separate judge model.

    `judge()` above uses the same local `llama3.2:1b` as the system under
    test -- a judge should ideally be at least as capable as what it grades,
    not identical to it. This project's "local models only" assumption (see
    README) rules out wiring a hosted API in by default, so this is left as
    an explicit extension point rather than silently using a weak judge: for
    the actual eval run in this repo's `eval/results/`, scoring was instead
    done manually by a more capable external model (documented there), and
    this function is where that would be automated -- e.g. swap in a larger
    local Ollama model, or call a hosted API, keeping the same (question,
    answer, grounding) -> score contract as `judge()`.

    Args:
        question: The question that was asked.
        answer: The agent's answer to grade.
        grounding: Reference fact/context to grade against, or "" if none.

    Raises:
        NotImplementedError: Always -- no external model is wired in here.
    """
    raise NotImplementedError(
        "Plug in a stronger/separate judge model here if you want automated "
        "judging independent of the system under test. Left unimplemented "
        "to avoid adding a required external API dependency/key by default."
    )
