import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "trackmeld-api"
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_health_db_endpoint(client: AsyncClient):
    response = await client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "reachable"


@pytest.mark.asyncio
async def test_get_station_by_code(client: AsyncClient):
    response = await client.get("/api/v1/stations/NDLS")
    assert response.status_code == 200
    data = response.json()
    assert data["station_code"] == "NDLS"
    assert data["station_name"] == "New Delhi"
    assert data["classification"] == "REAL"
    assert data["source_id"] == "SRC-TAG-2023-TBL-01"


@pytest.mark.asyncio
async def test_get_station_not_found(client: AsyncClient):
    response = await client.get("/api/v1/stations/NONEXISTENT99")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_section_by_code(client: AsyncClient):
    response = await client.get("/api/v1/sections/NDLS-GZB")
    assert response.status_code == 200
    data = response.json()
    assert data["section_code"] == "NDLS-GZB"
    assert data["length_km"] == 25.0
    assert data["classification"] == "DERIVED"


@pytest.mark.asyncio
async def test_get_train_by_number(client: AsyncClient):
    response = await client.get("/api/v1/trains/12301")
    assert response.status_code == 200
    data = response.json()
    assert data["train_number"] == "12301"
    assert "Rajdhani" in data["train_name"]
    assert data["classification"] == "REAL"


@pytest.mark.asyncio
async def test_get_rule_by_id(client: AsyncClient):
    response = await client.get("/api/v1/rules/RULE-STAT-RBP-1502C")
    assert response.status_code == 200
    data = response.json()
    assert data["rule_id"] == "RULE-STAT-RBP-1502C"
    assert data["safety_critical"] is True
    assert data["rule_class"] == "VERIFIED_SOURCE"
