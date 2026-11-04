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


def test_operations_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/operations").status_code == 401
    assert client.get("/api/v1/work-centers").status_code == 401
    assert client.get("/api/v1/coefficients").status_code == 401
    assert client.get("/api/v1/auxiliary-operations").status_code == 401
    assert client.get("/api/v1/drilling-rates").status_code == 401
    assert client.get("/api/v1/cooperation-services").status_code == 401


def test_list_and_update_operations(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    response = client.get("/api/v1/operations", headers=manager)
    assert response.status_code == 200
    operations = response.json()
    assert len(operations) == 3
    turning = next(op for op in operations if op["code"] == "TURN_CNC_EXT")
    assert turning["setup_time_base_min"] == "40.0"
    assert len(turning["rates"]) == 1
    rate = turning["rates"][0]
    assert rate["material_iso_group"] == "P"
    assert rate["q_rough_cm3_min"] == "48.000"
    assert rate["s_finish_dm2_min"] == "3.800"

    denied = client.patch(
        f"/api/v1/operations/{turning['id']}",
        json={"setup_time_base_min": "50.0"},
        headers=manager,
    )
    assert denied.status_code == 403

    updated = client.patch(
        f"/api/v1/operations/{turning['id']}",
        json={"setup_time_base_min": "50.0"},
        headers=admin,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["setup_time_base_min"] == "50.0"
    assert len(body["rates"]) == 1

    missing = client.patch(
        "/api/v1/operations/9999",
        json={"setup_time_base_min": "50.0"},
        headers=admin,
    )
    assert missing.status_code == 404


def test_update_operation_rate(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    operations = client.get("/api/v1/operations", headers=manager).json()
    turning = next(op for op in operations if op["code"] == "TURN_CNC_EXT")
    rate_id = turning["rates"][0]["id"]

    denied = client.patch(
        f"/api/v1/operation-rates/{rate_id}",
        json={"q_rough_cm3_min": "50.000"},
        headers=manager,
    )
    assert denied.status_code == 403

    updated = client.patch(
        f"/api/v1/operation-rates/{rate_id}",
        json={"q_rough_cm3_min": "50.000", "s_finish_dm2_min": "4.000"},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["q_rough_cm3_min"] == "50.000"
    assert updated.json()["s_finish_dm2_min"] == "4.000"

    missing = client.patch(
        "/api/v1/operation-rates/9999",
        json={"q_rough_cm3_min": "50.000"},
        headers=admin,
    )
    assert missing.status_code == 404


def test_list_and_update_work_centers(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    response = client.get("/api/v1/work-centers", headers=manager)
    assert response.status_code == 200
    centers = response.json()
    assert len(centers) == 3
    turn = next(c for c in centers if c["code"] == "TURN_CNC_01")
    assert turn["machine_rate_per_min"] == "30.0000"
    assert turn["machine_type"] == "TURNING_CNC"
    # Расточная ячейка TURNING_INT входит в перечень рабочих центров
    turning_int = next(c for c in centers if c["code"] == "TURN_INT_01")
    assert turning_int["machine_rate_per_min"] == "30.0000"

    denied = client.patch(
        f"/api/v1/work-centers/{turn['id']}",
        json={"machine_rate_per_min": "32.5000"},
        headers=manager,
    )
    assert denied.status_code == 403

    updated = client.patch(
        f"/api/v1/work-centers/{turn['id']}",
        json={"machine_rate_per_min": "32.5000"},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["machine_rate_per_min"] == "32.5000"

    missing = client.patch(
        "/api/v1/work-centers/9999",
        json={"machine_rate_per_min": "32.5000"},
        headers=admin,
    )
    assert missing.status_code == 404


def test_list_and_update_coefficients(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    response = client.get("/api/v1/coefficients", headers=manager)
    assert response.status_code == 200
    coefficients = response.json()
    assert len(coefficients) == 2
    it7 = next(c for c in coefficients if c["code"] == "IT7")
    assert it7["multiplier"] == "2.600"

    denied = client.patch(
        f"/api/v1/coefficients/{it7['id']}",
        json={"multiplier": "2.800"},
        headers=manager,
    )
    assert denied.status_code == 403

    updated = client.patch(
        f"/api/v1/coefficients/{it7['id']}",
        json={"multiplier": "2.800"},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["multiplier"] == "2.800"

    missing = client.patch(
        "/api/v1/coefficients/9999",
        json={"multiplier": "2.800"},
        headers=admin,
    )
    assert missing.status_code == 404


def test_list_and_update_auxiliary_operations(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    response = client.get("/api/v1/auxiliary-operations", headers=manager)
    assert response.status_code == 200
    operations = response.json()
    assert len(operations) == 2
    fitting = next(op for op in operations if op["code"] == "FITTING")
    assert fitting["fixed_time_min"] == "3.00"
    assert fitting["rate_per_min"] == "1.2000"

    denied = client.patch(
        f"/api/v1/auxiliary-operations/{fitting['id']}",
        json={"fixed_time_min": "4.00"},
        headers=manager,
    )
    assert denied.status_code == 403

    updated = client.patch(
        f"/api/v1/auxiliary-operations/{fitting['id']}",
        json={"fixed_time_min": "4.00", "is_active": False},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["fixed_time_min"] == "4.00"
    assert updated.json()["is_active"] is False

    missing = client.patch(
        "/api/v1/auxiliary-operations/9999",
        json={"fixed_time_min": "4.00"},
        headers=admin,
    )
    assert missing.status_code == 404


def test_list_and_update_drilling_rates(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    response = client.get("/api/v1/drilling-rates", headers=manager)
    assert response.status_code == 200
    rates = response.json()
    assert len(rates) == 5
    first = rates[0]
    assert first["diameter_from_mm"] == "3.0"
    assert first["diameter_to_mm"] == "5.5"
    assert first["carbide_feed_mm_min"] == "280.0"

    denied = client.patch(
        f"/api/v1/drilling-rates/{first['id']}",
        json={"carbide_feed_mm_min": "300.0"},
        headers=manager,
    )
    assert denied.status_code == 403

    updated = client.patch(
        f"/api/v1/drilling-rates/{first['id']}",
        json={"carbide_feed_mm_min": "300.0", "hss_feed_mm_min": "80.0"},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["carbide_feed_mm_min"] == "300.0"
    assert updated.json()["hss_feed_mm_min"] == "80.0"

    missing = client.patch(
        "/api/v1/drilling-rates/9999",
        json={"carbide_feed_mm_min": "300.0"},
        headers=admin,
    )
    assert missing.status_code == 404


def test_cooperation_services_crud(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    payload = {
        "service_type": "HEAT_TREATMENT",
        "unit": "KG",
        "price_per_unit": "85.00",
        "contractor": "Термо-Пром",
        "min_lot_qty": "20.00",
    }

    denied = client.post("/api/v1/cooperation-services", json=payload, headers=manager)
    assert denied.status_code == 403

    created = client.post("/api/v1/cooperation-services", json=payload, headers=admin)
    assert created.status_code == 201
    body = created.json()
    service_id = body["id"]
    assert body["service_type"] == "HEAT_TREATMENT"
    assert body["price_per_unit"] == "85.00"
    assert body["contractor"] == "Термо-Пром"

    listing = client.get("/api/v1/cooperation-services", headers=manager)
    assert listing.status_code == 200
    count_after_create = len(listing.json())
    assert count_after_create >= 3  # seed conftest (термо + гальваника) + новая

    updated = client.patch(
        f"/api/v1/cooperation-services/{service_id}",
        json={"price_per_unit": "92.50"},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["price_per_unit"] == "92.50"

    deleted = client.delete(f"/api/v1/cooperation-services/{service_id}", headers=admin)
    assert deleted.status_code == 204

    gone = client.get("/api/v1/cooperation-services", headers=manager)
    assert len(gone.json()) == count_after_create - 1

    missing = client.delete("/api/v1/cooperation-services/9999", headers=admin)
    assert missing.status_code == 404


def test_capacity_load_crud(client: TestClient) -> None:
    manager = _auth(_login(client, MANAGER_EMAIL))
    admin = _auth(_login(client, ADMIN_EMAIL))

    listing = client.get("/api/v1/capacity", headers=manager)
    assert listing.status_code == 200
    rows = listing.json()
    turning = next(r for r in rows if r["work_center_group"] == "TURNING_CNC")
    assert turning["utilization_percent"] == 30.0

    denied = client.patch(
        f"/api/v1/capacity/{turning['id']}",
        json={"scheduled_minutes": "95000.00"},
        headers=manager,
    )
    assert denied.status_code == 403

    # 30% → 95%: utilization (generated) пересчитывается
    updated = client.patch(
        f"/api/v1/capacity/{turning['id']}",
        json={"scheduled_minutes": "95000.00"},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["utilization_percent"] == 95.0

    created = client.post(
        "/api/v1/capacity",
        json={
            "work_center_group": "MILLING_3AXIS",
            "total_fund_minutes": "100000.00",
            "scheduled_minutes": "20000.00",
        },
        headers=admin,
    )
    assert created.status_code == 201
    assert created.json()["utilization_percent"] == 20.0

    conflict = client.post(
        "/api/v1/capacity",
        json={
            "work_center_group": "MILLING_3AXIS",
            "total_fund_minutes": "100000.00",
        },
        headers=admin,
    )
    assert conflict.status_code == 409

    missing = client.patch(
        "/api/v1/capacity/9999",
        json={"scheduled_minutes": "1.00"},
        headers=admin,
    )
    assert missing.status_code == 404
