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


def _paginated_payload(sample_payload):
    import copy

    payload = copy.deepcopy(sample_payload)
    for entity in payload["included"]:
        if entity.get("entityUrn") == "urn:li:collectionResponse:skills-page-1":
            entity["paging"]["total"] = 4
            break
    return payload


@pytest.mark.asyncio
@respx.mock
async def test_skills_pagination_merges(client, voyager_url, sample_payload):
    settings = get_settings()
    payload = _paginated_payload(sample_payload)
    respx.get(voyager_url).mock(return_value=httpx.Response(200, json=payload))
    skills_url = (
        f"{settings.voyager_base_url}/voyager/api/identity/dash/profileSkills"
        f"?q=memberIdentity&memberIdentity=john-doe"
        f"&decorationId={settings.skills_decoration_id}"
        f"&start=2&count={settings.skills_page_size}"
    )
    skills_page = {
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
                "entityUrn": "urn:li:fsd_skill:(ACoAAB123456789,3)",
                "name": "Docker",
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
                "entityUrn": "urn:li:fsd_skill:(ACoAAB123456789,4)",
                "name": "Kubernetes",
            },
        ]
    }
    skills_route = respx.get(skills_url).mock(
        return_value=httpx.Response(200, json=skills_page)
    )

    response = await client.get("/api/profile", params={"url": "john-doe"})
    assert response.status_code == 200
    data = response.json()
    assert [s["name"] for s in data["skills"]] == [
        "Python",
        "FastAPI",
        "Docker",
        "Kubernetes",
    ]
    assert skills_route.call_count == 1
    assert len(data["treasury_media"]) == 2


@pytest.mark.asyncio
@respx.mock
async def test_skills_pagination_failure_keeps_first_page(
    client, voyager_url, sample_payload
):
    settings = get_settings()
    payload = _paginated_payload(sample_payload)
    respx.get(voyager_url).mock(return_value=httpx.Response(200, json=payload))
    skills_url = (
        f"{settings.voyager_base_url}/voyager/api/identity/dash/profileSkills"
        f"?q=memberIdentity&memberIdentity=john-doe"
        f"&decorationId={settings.skills_decoration_id}"
        f"&start=2&count={settings.skills_page_size}"
    )
    respx.get(skills_url).mock(return_value=httpx.Response(404, json={}))
    from urllib.parse import quote

    fallback = (
        f"{settings.voyager_base_url}/voyager/api/identity/dash/profiles/"
        f"{quote('urn:li:fsd_profile:ACoAAB123456789', safe='')}/skills"
        f"?start=2&count={settings.skills_page_size}"
    )
    respx.get(fallback).mock(return_value=httpx.Response(404, json={}))

    response = await client.get("/api/profile", params={"url": "john-doe"})
    assert response.status_code == 200
    assert [s["name"] for s in response.json()["skills"]] == ["Python", "FastAPI"]
