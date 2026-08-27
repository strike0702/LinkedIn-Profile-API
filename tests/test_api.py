import json
from pathlib import Path

import httpx
import pytest
import respx
from httpx import ASGITransport

from app.config import get_settings
from app.main import app
from app.services.cache import InMemoryTTLCache
from app.services.profile_service import ProfileService, _profile_cache


@pytest.fixture(autouse=True)
def clear_profile_cache():
    _profile_cache.clear()
    yield
    _profile_cache.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def voyager_url():
    settings = get_settings()
    return (
        f"{settings.voyager_base_url}/voyager/api/identity/dash/profiles"
        f"?q=memberIdentity&memberIdentity=john-doe"
        f"&decorationId={settings.decoration_id}"
    )


@pytest.fixture
def sample_payload():
    path = Path(__file__).parent / "fixtures" / "voyager_sample.json"
    with path.open() as f:
        return json.load(f)


@pytest.mark.asyncio
@respx.mock
async def test_get_profile_success(client, voyager_url, sample_payload):
    respx.get(voyager_url).mock(return_value=httpx.Response(200, json=sample_payload))

    response = await client.get("/api/profile", params={"url": "john-doe"})
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["public_identifier"] == "john-doe"


@pytest.mark.asyncio
@respx.mock
async def test_post_profile_success(client, voyager_url, sample_payload):
    respx.get(voyager_url).mock(return_value=httpx.Response(200, json=sample_payload))

    response = await client.post("/api/profile", json={"url": "https://www.linkedin.com/in/john-doe/"})
    assert response.status_code == 200
    assert response.json()["headline"] == "Software Engineer at Acme Corp"


@pytest.mark.asyncio
@respx.mock
async def test_profile_unauthorized(client, voyager_url):
    respx.get(voyager_url).mock(return_value=httpx.Response(401, json={"message": "Unauthorized"}))

    response = await client.get("/api/profile", params={"url": "john-doe"})
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "unauthorized"
    assert body["status"] == 401


@pytest.mark.asyncio
@respx.mock
async def test_profile_not_found(client, voyager_url):
    respx.get(voyager_url).mock(return_value=httpx.Response(404, json={"message": "Not found"}))

    response = await client.get("/api/profile", params={"url": "john-doe"})
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_profile_rate_limited(client, voyager_url):
    respx.get(voyager_url).mock(
        return_value=httpx.Response(429, json={"message": "Too many requests"})
    )

    response = await client.get("/api/profile", params={"url": "john-doe"})
    assert response.status_code == 429
    body = response.json()
    assert body["error"] == "rate_limit_exceeded"


@pytest.mark.asyncio
async def test_invalid_url(client):
    response = await client.get("/api/profile", params={"url": "https://twitter.com/user"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "invalid_url"


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@respx.mock
async def test_cache_hit(client, voyager_url, sample_payload):
    cache = InMemoryTTLCache()
    route = respx.get(voyager_url).mock(return_value=httpx.Response(200, json=sample_payload))

    from app.core.voyager_client import VoyagerClient

    service = ProfileService(voyager=VoyagerClient(), cache=cache)

    await service.get_profile("john-doe")
    await service.get_profile("john-doe")

    assert route.call_count == 1
    await service.close()
