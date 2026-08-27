import os

# Set test env before app imports (Settings validates at import time via routes)
os.environ.setdefault("LI_AT", "test_li_at_value")
os.environ.setdefault("JSESSIONID", "ajax:1234567890")
os.environ.setdefault("USER_AGENT", "TestAgent/1.0")
os.environ.setdefault("CACHE_TTL_SECONDS", "60")
os.environ.setdefault("RATE_LIMIT", "1000/minute")

import pytest


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    monkeypatch.setenv("LI_AT", "test_li_at_value")
    monkeypatch.setenv("JSESSIONID", "ajax:1234567890")
    monkeypatch.setenv("USER_AGENT", "TestAgent/1.0")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "60")
    monkeypatch.setenv("RATE_LIMIT", "1000/minute")
    # Clear settings cache between tests
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def voyager_sample():
    import json
    from pathlib import Path

    path = Path(__file__).parent / "fixtures" / "voyager_sample.json"
    with path.open() as f:
        return json.load(f)
