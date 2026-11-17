"""Shared helpers for recorded HTML fixtures (used by record_fixtures.py and conftest.py)."""

import hashlib
import json
from pathlib import Path

HTML_DIR = Path(__file__).parent / "fixtures" / "html"
MANIFEST = HTML_DIR / "manifest.json"

# Events recorded for the end-to-end scrape tests.
#   TP_5GGDDHUF8D — Lisbon Race 6 TRYKA PRO: solo athletes, M + W.
#   TR_5GGDDHUF7A — London Race 5 TRYKA RELAY: 4-person teams across M/W/X, and
#                   includes placeholder teams (numeric member names) that must be dropped.
E2E_EVENTS = ["TP_5GGDDHUF8D", "TR_5GGDDHUF7A"]

# A single list page from a large event, so pagination parsing is covered.
PAGINATED_LIST = (
    1,
    {
        "content": "list",
        "fpid": "list",
        "pid": "list",
        "lang": "EN_CAP",
        "event": "T8_5GGDDHUF8D",
        "search[age_class]": "%",
        "search[sex]": "M",
        "page": 1,
    },
)


def fixture_key(series: int, params: dict) -> str:
    canonical = json.dumps([series, sorted((k, str(v)) for k, v in params.items())])
    return hashlib.sha1(canonical.encode()).hexdigest()[:16]


def fixture_path(series: int, params: dict) -> Path:
    return HTML_DIR / f"{fixture_key(series, params)}.html"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
