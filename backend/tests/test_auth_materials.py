from fastapi.testclient import TestClient

from tests.conftest import ADMIN_EMAIL, MANAGER_EMAIL, PASSWORD

MATERIAL = {
    "grade": "Сталь 45",
    "gost": "ГОСТ 1050-2013",
    "iso_group": "P",
    "density_g_cm3": "7.8500",
    "machinability_factor": "1.00",
    "cost_per_kg": "120.50",
    "scrap_price_per_kg": "15.00",
}


def _login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_invalid_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me(client: TestClient) -> None:
    token = _login(client, ADMIN_EMAIL)
    response = client.get("/api/v1/auth/me", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_material_rbac_flow(client: TestClient) -> None:
    admin = _auth(_login(client, ADMIN_EMAIL))
    manager = _auth(_login(client, MANAGER_EMAIL))

    response = client.post("/api/v1/materials", json=MATERIAL, headers=manager)
    assert response.status_code == 403

    response = client.get("/api/v1/materials")
    assert response.status_code == 401

    response = client.post("/api/v1/materials", json=MATERIAL, headers=admin)
    assert response.status_code == 201
    material_id = response.json()["id"]

    response = client.post("/api/v1/materials", json=MATERIAL, headers=admin)
    assert response.status_code == 409

    response = client.get("/api/v1/materials", headers=manager)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.patch(
        f"/api/v1/materials/{material_id}",
        json={"cost_per_kg": "130.00"},
        headers=manager,
    )
    assert response.status_code == 403

    response = client.patch(
        f"/api/v1/materials/{material_id}",
        json={"cost_per_kg": "130.00"},
        headers=admin,
    )
    assert response.status_code == 200
    assert response.json()["cost_per_kg"] == "130.00"

    response = client.delete(f"/api/v1/materials/{material_id}", headers=admin)
    assert response.status_code == 204

    response = client.get(f"/api/v1/materials/{material_id}", headers=admin)
    assert response.status_code == 404
