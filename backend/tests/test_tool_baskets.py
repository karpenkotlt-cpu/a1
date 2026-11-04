from fastapi.testclient import TestClient

from tests.conftest import ADMIN_EMAIL, MANAGER_EMAIL, PASSWORD


def _login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_tool_baskets_require_auth(client: TestClient) -> None:
    response = client.get("/api/v1/tool-baskets")
    assert response.status_code == 401


def test_list_and_update_tool_baskets(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    response = client.get("/api/v1/tool-baskets", headers=manager)
    assert response.status_code == 200
    baskets = response.json()
    assert len(baskets) == 2
    drill = next(b for b in baskets if b["operation_group"] == "DRILL_CARBIDE")
    assert drill["regrindable"] is True
    assert drill["diameter_from_mm"] == "11.0"

    denied = client.patch(
        f"/api/v1/tool-baskets/{drill['id']}",
        json={"tool_set_cost": "9999.00"},
        headers=manager,
    )
    assert denied.status_code == 403

    updated = client.patch(
        f"/api/v1/tool-baskets/{drill['id']}",
        json={"tool_set_cost": "9999.00", "tool_life_min": "60"},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["tool_set_cost"] == "9999.00"
    assert updated.json()["tool_life_min"] == "60.00"
