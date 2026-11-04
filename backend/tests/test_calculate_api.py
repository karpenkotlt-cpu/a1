import pytest
from fastapi.testclient import TestClient

from tests.conftest import ADMIN_EMAIL, MANAGER_EMAIL, PASSWORD

DOCX_CONTRACT = {
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
        },
        {
            "type": "HOLE_ARRAY",
            "count": 4,
            "diameter": 6.0,
            "depth": 15.0,
            "is_through": False,
            "tolerance": "IT7",
            "thread": "M6",
        },
    ],
    "margin_percent": "35.00",
}


def _login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": MANAGER_EMAIL, "password": PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def test_calculate_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/calculate/25d-feature", json=DOCX_CONTRACT)
    assert response.status_code == 401


def test_calculate_rejects_unknown_template(client: TestClient) -> None:
    token = _login(client)
    payload = {**DOCX_CONTRACT, "base_template": {"type": "T9_UNKNOWN"}}
    response = client.post(
        "/api/v1/calculate/25d-feature",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_calculate_docx_contract(client: TestClient) -> None:
    token = _login(client)
    response = client.post(
        "/api/v1/calculate/25d-feature",
        json=DOCX_CONTRACT,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["v_net_cm3"] > 0
    assert body["v_removed_cm3"] > 0
    assert body["m_gross_kg"] > body["m_net_kg"] > 0
    assert body["machine_time_min"] > 0
    assert body["setup_time_min"] == 85.0
    assert {op["code"] for op in body["operations"]} == {
        "TURN_CNC_EXT",
        "TURN_CNC_INT",
        "FITTING",
        "QC",
    }
    assert float(body["price_per_part"]) > 0
    assert float(body["batch_total_price"]) == pytest.approx(
        float(body["price_per_part"]) * 20, abs=1.0
    )


def test_calculate_t5_housing(client: TestClient) -> None:
    token = _login(client)
    payload = {
        **DOCX_CONTRACT,
        "base_template": {
            "type": "T5_HOUSING",
            "dimensions": {
                "length": 200.0,
                "width": 100.0,
                "height": 60.0,
                "removal_ratio": 0.6,
            },
        },
        "batch_size": 10,
        "features": [
            {
                "type": "HOLE_ARRAY",
                "count": 4,
                "diameter": 11.0,
                "depth": 20.0,
                "tolerance": "IT11",
                "counterbore_diameter": 18.0,
                "counterbore_depth": 5.0,
            }
        ],
    }
    response = client.post(
        "/api/v1/calculate/25d-feature",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["v_net_cm3"] > 0
    assert body["m_gross_kg"] > body["m_net_kg"] > 0
    assert body["setup_time_min"] == 45.0


def test_calculate_tolerance_penalty_applied(client: TestClient) -> None:
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    strict = client.post(
        "/api/v1/calculate/25d-feature", json=DOCX_CONTRACT, headers=headers
    )
    relaxed = client.post(
        "/api/v1/calculate/25d-feature",
        json={
            **DOCX_CONTRACT,
            "margin_percent": "35.00",
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
        },
        headers=headers,
    )
    assert strict.status_code == 200
    assert relaxed.status_code == 200
    strict_time = strict.json()["machine_time_min"]
    relaxed_time = relaxed.json()["machine_time_min"]
    assert strict_time > relaxed_time


def test_calculate_with_cooperation(client: TestClient) -> None:
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    services = client.get("/api/v1/cooperation-services", headers=headers).json()
    heat = next(s for s in services if s["service_type"] == "HEAT_TREATMENT")
    galv = next(s for s in services if s["service_type"] == "GALVANIZING")

    # KG — авто-количество по массе; DM2 — ручное количество.
    payload = {
        **DOCX_CONTRACT,
        "cooperation": [
            {"service_id": heat["id"]},
            {"service_id": galv["id"], "qty_override": "5.000"},
        ],
    }
    response = client.post(
        "/api/v1/calculate/25d-feature", json=payload, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    m_net = body["m_net_kg"]
    expected_heat = round(m_net * 85.00, 2)
    expected_total = round(expected_heat + 5 * 40.00, 2)
    assert float(body["cooperation_cost"]) == pytest.approx(expected_total, abs=0.5)
    units = {line["unit"]: line for line in body["cooperations"]}
    assert units["KG"]["unit_price"] == "85.00"
    assert units["DM2"]["qty"] == "5.000"
    assert units["DM2"]["cost"] == "200.00"

    # Без кооперации цена строго ниже (Ccoop входит до наценки).
    plain = client.post(
        "/api/v1/calculate/25d-feature", json=DOCX_CONTRACT, headers=headers
    )
    assert plain.status_code == 200
    assert float(body["price_per_part"]) > float(plain.json()["price_per_part"])


def test_calculate_cooperation_moq_amortized(client: TestClient) -> None:
    """MOQ 20 кг при партии 1 шт → 20 кг/деталь, а не масса детали."""
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    services = client.get("/api/v1/cooperation-services", headers=headers).json()
    heat = next(s for s in services if s["service_type"] == "HEAT_TREATMENT")

    payload = {
        **DOCX_CONTRACT,
        "batch_size": 1,
        "cooperation": [{"service_id": heat["id"]}],
    }
    response = client.post(
        "/api/v1/calculate/25d-feature", json=payload, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    line = body["cooperations"][0]
    assert float(line["qty"]) == pytest.approx(20.0)
    assert line["cost"] == "1700.00"


def test_calculate_cooperation_unknown_service(client: TestClient) -> None:
    token = _login(client)
    payload = {
        **DOCX_CONTRACT,
        "cooperation": [{"service_id": 9999}],
    }
    response = client.post(
        "/api/v1/calculate/25d-feature",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "9999" in response.json()["detail"]


def test_batch_ladder(client: TestClient) -> None:
    token = _login(client)
    response = client.post(
        "/api/v1/calculate/25d-feature/ladder",
        json=DOCX_CONTRACT,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    rungs = response.json()
    sizes = [rung["batch_size"] for rung in rungs]
    # 1/5/10/25/50/100 + текущая партия 20 из DOCX_CONTRACT
    assert sizes == [1, 5, 10, 20, 25, 50, 100]
    prices = [float(rung["price_per_part"]) for rung in rungs]
    # Амортизация Tпз: цена за деталь убывает с тиражом
    assert prices == sorted(prices, reverse=True)
    assert prices[0] > prices[-1]
    for rung in rungs:
        assert float(rung["batch_total_price"]) == pytest.approx(
            float(rung["price_per_part"]) * rung["batch_size"], abs=1.0
        )


def test_batch_ladder_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/calculate/25d-feature/ladder", json=DOCX_CONTRACT)
    assert response.status_code == 401


def test_dynamic_margin_by_capacity(client: TestClient) -> None:
    """TURNING_CNC загружена на 30% (seed) → Kmargin 0.55 для токарных T2;
    фрезерная группа без строки APS → Kmargin 1.0."""
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    turned = client.post(
        "/api/v1/calculate/25d-feature", json=DOCX_CONTRACT, headers=headers
    )
    assert turned.status_code == 200
    body = turned.json()
    assert body["margin_multiplier"] == 0.55
    assert body["capacity_utilization_percent"] == 30.0

    milled = client.post(
        "/api/v1/calculate/25d-feature",
        json={
            **DOCX_CONTRACT,
            "base_template": {
                "type": "T4_PLATE",
                "dimensions": {"length": 200.0, "width": 100.0, "height": 40.0},
            },
        },
        headers=headers,
    )
    assert milled.status_code == 200
    assert milled.json()["margin_multiplier"] == 1.0
    assert milled.json()["capacity_utilization_percent"] is None


def test_bottleneck_is_max_across_route_groups(client: TestClient) -> None:
    """Узкое место маршрута = max(Ugroup) по ВСЕМ группам маршрута
    (T2: главная TURNING_CNC + расточка TURNING_INT), а не только
    по группе главного станка."""
    admin_token = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": PASSWORD},
    ).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    headers = {"Authorization": f"Bearer {_login(client)}"}

    # Расточная ячейка загружена ниже главной (20% < 30%) — узкое место
    # остаётся TURNING_CNC.
    created = client.post(
        "/api/v1/capacity",
        json={
            "work_center_group": "TURNING_INT",
            "total_fund_minutes": "100000.00",
            "scheduled_minutes": "20000.00",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201

    calm = client.post(
        "/api/v1/calculate/25d-feature", json=DOCX_CONTRACT, headers=headers
    )
    assert calm.status_code == 200
    body = calm.json()
    assert body["bottleneck_group"] == "TURNING_CNC"
    assert body["capacity_utilization_percent"] == 30.0
    assert body["margin_multiplier"] == 0.55

    # Перегруз расточной ячейки (96% > 95%) — она становится узким местом
    # маршрута: Surge Kmargin 2.0, хотя главный станок загружен на 30%.
    patched = client.patch(
        f"/api/v1/capacity/{created.json()['id']}",
        json={"scheduled_minutes": "96000.00"},
        headers=admin_headers,
    )
    assert patched.status_code == 200

    hot = client.post(
        "/api/v1/calculate/25d-feature", json=DOCX_CONTRACT, headers=headers
    )
    assert hot.status_code == 200
    body = hot.json()
    assert body["bottleneck_group"] == "TURNING_INT"
    assert body["capacity_utilization_percent"] == 96.0
    assert body["margin_multiplier"] == 2.0
    assert float(body["price_per_part"]) > float(calm.json()["price_per_part"])


def test_floor_price_in_response(client: TestClient) -> None:
    """Пол цены (переменные издержки, антидемпинг): есть в ответе, ниже
    цены при марже 35%, растёт с кооперацией (Ccoop входит в пол)."""
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    plain = client.post(
        "/api/v1/calculate/25d-feature", json=DOCX_CONTRACT, headers=headers
    )
    assert plain.status_code == 200
    body = plain.json()
    floor = body["floor_price_per_part"]
    assert floor is not None
    assert float(floor) > 0
    assert float(floor) < float(body["price_per_part"])

    services = client.get("/api/v1/cooperation-services", headers=headers).json()
    heat = next(s for s in services if s["service_type"] == "HEAT_TREATMENT")
    with_coop = client.post(
        "/api/v1/calculate/25d-feature",
        json={**DOCX_CONTRACT, "cooperation": [{"service_id": heat["id"]}]},
        headers=headers,
    )
    assert with_coop.status_code == 200
    assert float(with_coop.json()["floor_price_per_part"]) > float(floor)
