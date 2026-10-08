import json
from pathlib import Path

CASES_DIR = Path(__file__).parent / "cases"


def load_cases(domain: str | None = None) -> list[dict]:
    """Load eval cases from the JSON files under `eval/cases/`.

    Args:
        domain: If given, only load cases from `eval/cases/<domain>.json`.
            Otherwise, load every domain's cases.

    Returns:
        A flat list of case dicts, each tagged with a "domain" key taken
        from its source filename.
    """
    files = [CASES_DIR / f"{domain}.json"] if domain else sorted(CASES_DIR.glob("*.json"))

    cases = []
    for path in files:
        for case in json.loads(path.read_text()):
            cases.append({**case, "domain": path.stem})
    return cases
