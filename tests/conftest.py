import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import scraper  # noqa: E402
from fixture_store import fixture_key, fixture_path  # noqa: E402


@pytest.fixture
def replay_fetch(monkeypatch):
    """Serve scraper.fetch from recorded HTML. Never touches the network."""

    def fake_fetch(session, series, params):
        path = fixture_path(series, params)
        if not path.exists():
            raise AssertionError(
                f"No recorded page for series={series} params={params} "
                f"(key {fixture_key(series, params)}). Re-run tests/record_fixtures.py."
            )
        return path.read_text(encoding="utf-8")

    monkeypatch.setattr(scraper, "fetch", fake_fetch)
    monkeypatch.setattr(scraper, "REQUEST_DELAY", 0)

    # Belt and braces: fail if anything tries a real HTTP request.
    def no_network(*args, **kwargs):
        raise AssertionError("Tests must not make network requests")

    monkeypatch.setattr("requests.Session.request", no_network)
    return fake_fetch


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def recorded_page():
    """Load the recorded page for (series, params)."""

    def load(series: int, params: dict) -> str:
        return fixture_path(series, params).read_text(encoding="utf-8")

    return load
