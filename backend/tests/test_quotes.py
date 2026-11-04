from fastapi.testclient import TestClient

from tests.conftest import ADMIN_EMAIL, MANAGER_EMAIL, PASSWORD

QUOTE_REQUEST = {
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "batch_size": 20,
    "material": {
        "iso_group": "P",
        "k_mach_rough": "1.00",
        "k_mach_finish": "1.00",
        "density_g_cm3": "7.85",
        "cost_per_kg": "120.50",
        "scrap_price_per_kg": "15.00",
    },
    "base_template": {
        "type": "T2_BUSHING",
        "dimensions": {
            "outer_steps": [
                {"diameter": 160.0, "length": 20.0},
                {"diameter": 100.0, "length": 60.0},
            ],
            "inner_steps": [
                {"diameter": 72.0, "length": 35.0},
                {"diameter": 60.0, "length": 45.0},
            ],
        },
    },
    "features": [
        {
            "type": "HOLE_ARRAY",
            "count": 6,
            "diameter": 11.0,
            "depth": 20.0,
            "is_through": True,
            "tolerance": "IT11",
            "thread": None,
        }
    ],
    "margin_percent": "35.00",
}


def _login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payload() -> dict[str, object]:
    return {"name": "Корпус подшипника", "material_id": None, "request": QUOTE_REQUEST}


def test_create_quote_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/quotes", json=_payload())
    assert response.status_code == 401


def test_create_and_list_quote(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    response = client.post("/api/v1/quotes", json=_payload(), headers=manager)
    assert response.status_code == 201
    body = response.json()
    assert float(body["price_per_part"]) > 0
    assert body["author_email"] == MANAGER_EMAIL
    assert body["request"]["base_template"]["type"] == "T2_BUSHING"
    assert body["result"]["m_net_kg"] > 0

    response = client.get("/api/v1/quotes", headers=manager)
    assert response.status_code == 200
    assert len(response.json()) == 1

    detail = client.get("/api/v1/quotes/1", headers=manager)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Корпус подшипника"


def test_export_quote_xlsx(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    response = client.post("/api/v1/quotes", json=_payload(), headers=manager)
    assert response.status_code == 201
    quote_id = response.json()["id"]

    export = client.get(f"/api/v1/quotes/{quote_id}/export.xlsx", headers=manager)
    assert export.status_code == 200
    assert export.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml"
    )
    assert export.content[:2] == b"PK"
    assert len(export.content) > 1000


def test_delete_quote_permissions(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    response = client.post("/api/v1/quotes", json=_payload(), headers=admin)
    assert response.status_code == 201
    quote_id = response.json()["id"]

    denied = client.delete(f"/api/v1/quotes/{quote_id}", headers=manager)
    assert denied.status_code == 403

    allowed = client.delete(f"/api/v1/quotes/{quote_id}", headers=admin)
    assert allowed.status_code == 204

    missing = client.delete(f"/api/v1/quotes/{quote_id}", headers=admin)
    assert missing.status_code == 404


def _t4_request(length: float) -> dict[str, object]:
    return {
        **QUOTE_REQUEST,
        "base_template": {
            "type": "T4_PLATE",
            "dimensions": {"length": length, "width": 100.0, "height": 40.0},
        },
    }


def test_find_analogues(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    client.post(
        "/api/v1/quotes",
        json={"name": "Плита 200", "material_id": None, "request": _t4_request(200)},
        headers=manager,
    )
    client.post(
        "/api/v1/quotes",
        json={"name": "Плита 240", "material_id": None, "request": _t4_request(240)},
        headers=manager,
    )
    client.post(
        "/api/v1/quotes",
        json=_payload(),  # T2 втулка — другой шаблон
        headers=manager,
    )

    query = {
        "template_type": "T4_PLATE",
        "iso_group": "P",
        "length_mm": 200.0,
        "width_mm": 100.0,
        "height_mm": 40.0,
    }
    response = client.post("/api/v1/quotes/similar", json=query, headers=manager)
    assert response.status_code == 200
    analogues = response.json()
    names = [a["name"] for a in analogues]
    assert names == ["Плита 200", "Плита 240"]
    assert analogues[0]["deviation_percent"] == 0.0
    assert analogues[1]["deviation_percent"] == 20.0
    assert float(analogues[0]["price_per_part"]) > 0

    # Жёсткий допуск отсекает 240-ю плиту
    strict = client.post(
        "/api/v1/quotes/similar",
        json={**query, "tolerance_percent": 10.0},
        headers=manager,
    )
    assert [a["name"] for a in strict.json()] == ["Плита 200"]

    # Другая ISO-группа — пусто
    other_iso = client.post(
        "/api/v1/quotes/similar",
        json={**query, "iso_group": "S"},
        headers=manager,
    )
    assert other_iso.json() == []

    # Неполные габариты токарного шаблона — 422
    invalid = client.post(
        "/api/v1/quotes/similar",
        json={"template_type": "T1_STEPPED_SHAFT", "length_mm": 100.0},
        headers=manager,
    )
    assert invalid.status_code == 422


def test_find_analogues_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/quotes/similar", json={"template_type": "T4_PLATE"})
    assert response.status_code == 401
