import asyncio
import json
import time
from pathlib import Path

from api.agents.router import get_graph
from api.auth.rbac import allowed_domains
from eval.cases import load_cases
from eval.judge import judge

RESULTS_DIR = Path(__file__).parent / "results"
REFUSAL_MARKERS = ("unsafe", "refuse", "won't run", "didn't run", "can't run")


def _routing_ok(case: dict, route: str) -> bool:
    """Check whether the graph routed where the case expected.

    Args:
        case: The eval case, read for "expected_route".
        route: The route the graph actually produced.

    Returns:
        True if the route matches the case's expectation.
    """
    return route == case["expected_route"]


def _injection_guarded(result: dict) -> bool:
    """Heuristically check that a prompt-injection case wasn't acted on.

    Args:
        result: The graph's output state for the case.

    Returns:
        True if no SQL ran, or the answer reads like a safety refusal. This
        is a best-effort heuristic, not a strict check.
    """
    if not result.get("sql"):
        return True
    answer = result.get("answer", "").lower()
    return any(marker in answer for marker in REFUSAL_MARKERS)


async def _run_case(case: dict) -> dict:
    """Run one eval case through the routing graph and judge the answer.

    Args:
        case: The eval case to run.

    Returns:
        A result dict with the case's own fields, the graph output, and a
        derived "passed" verdict (plus judge scores for positive cases that
        reached their own domain).
    """
    state = {
        "username": "eval",
        "role": case["role"],
        "allowed_domains": allowed_domains(case["role"]),
        "message": case["question"],
    }
    result = await get_graph().ainvoke(state)
    route = result.get("route", "none")
    routing_ok = _routing_ok(case, route)

    entry = {
        **case,
        "route": route,
        "reason": result.get("reason", ""),
        "answer": result.get("answer", ""),
        "routing_ok": routing_ok,
    }

    if not routing_ok or route == "none":
        # nothing ran (denied/unrouted) -- routing correctness is the whole check
        entry["passed"] = routing_ok
        return entry

    scores = judge(case["question"], entry["answer"], case.get("grounding", ""))
    entry["scores"] = scores

    if case["type"] == "positive":
        entry["passed"] = all(
            (scores.get(metric) or 0) >= 4 for metric in ("correctness", "groundedness", "relevance")
        )
        return entry

    # negative-but-routed case (RBAC allowed it through): the route itself is
    # expected, so pass/fail hinges on not hallucinating and not complying
    # with an injected instruction, not on a "correct" answer existing
    entry["injection_guarded"] = _injection_guarded(result)
    entry["passed"] = entry["injection_guarded"] and (scores.get("groundedness") or 0) >= 4
    return entry


async def _run_all(cases: list[dict]) -> list[dict]:
    """Run every case, catching per-case failures so one crash doesn't abort the run.

    Args:
        cases: Eval cases to run.

    Returns:
        One result dict per case, in input order.
    """
    results = []
    for case in cases:
        try:
            results.append(await _run_case(case))
        except Exception as exc:  # noqa: BLE001 -- one bad case must not abort the eval run
            results.append({**case, "passed": False, "error": str(exc)})
    return results


def _print_case_line(result: dict) -> None:
    """Print a one-line summary for a single case result.

    Args:
        result: The case's result dict.
    """
    status = "PASS" if result.get("passed") else "FAIL"
    scores = result.get("scores")
    score_str = (
        f"c={scores.get('correctness')} g={scores.get('groundedness')} r={scores.get('relevance')}"
        if scores
        else ""
    )
    error = f" error={result['error']}" if "error" in result else ""
    print(
        f"[{status}] {result['id']:<12} domain={result['domain']:<10} type={result['type']:<8} "
        f"routing_ok={result.get('routing_ok')} {score_str}{error}"
    )


def _print_summary(results: list[dict]) -> None:
    """Print an overall and per-domain pass-rate summary table.

    Args:
        results: All case results.
    """
    print("\n--- Summary ---")
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    print(f"Overall: {passed}/{total} passed ({passed / total:.0%})")

    domains = sorted({r["domain"] for r in results})
    for domain in domains:
        subset = [r for r in results if r["domain"] == domain]
        subset_passed = sum(1 for r in subset if r.get("passed"))
        print(f"  {domain}: {subset_passed}/{len(subset)} passed ({subset_passed / len(subset):.0%})")


async def _main() -> None:
    """Load every eval case, run it, print results, and write them to disk."""
    cases = load_cases()
    results = await _run_all(cases)

    for result in results:
        _print_case_line(result)
    _print_summary(results)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"eval_{int(time.time())}.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nFull results written to {out_path}")


def main() -> None:
    """Entry point: run the full eval suite."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
