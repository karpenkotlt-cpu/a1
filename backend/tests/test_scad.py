"""Фаза A внедрения OpenSCAD: юнит-тесты подмены геометрии, регрессия
«без scad_code — побитово прежний ответ», интеграция с реальным бинарником."""

import asyncio
import base64
import math

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain.dto.calculation import CalculateRequestDTO
from app.domain.engine import geometry, scad_metrics
from app.services import scad_compiler
from tests.conftest import MANAGER_EMAIL, PASSWORD
from tests.test_calculate_api import DOCX_CONTRACT

T1_SHAFT = {
    **DOCX_CONTRACT,
    "base_template": {
        "type": "T1_STEPPED_SHAFT",
        "dimensions": {
            "steps": [
                {"diameter": 20.0, "length": 30.0},
                {"diameter": 10.0, "length": 20.0},
            ]
        },
    },
    "features": [],
}

T1_SHAFT_SCAD = (
    "union() {\n"
    "  cylinder(h=30, d=20, $fn=96);\n"
    "  translate([0, 0, 30]) cylinder(h=20, d=10, $fn=96);\n"
    "}\n"
)


def _login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": MANAGER_EMAIL, "password": PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _mesh(
    volume_mm3: float, area_mm2: float, extents: tuple[float, float, float]
) -> scad_metrics.MeshMeasurements:
    return scad_metrics.MeshMeasurements(
        extents_mm=extents, volume_mm3=volume_mm3, area_mm2=area_mm2
    )


# ---------------------------------------------------------------- unit


def test_build_override_cylinder_keeps_analytic_gross() -> None:
    """v_net — из сетки; v_gross — аналитическая заготовка geometry.py."""
    request = CalculateRequestDTO.model_validate(
        {**T1_SHAFT, "batch_size": 1, "cooperation": []}
    )
    analytic = geometry.net_metrics(request)
    # вал: π/4·20²·30 + π/4·10²·20 = 10995.57 мм³; боковая + торцы
    v_net = math.pi / 4 * (20**2) * 30 + math.pi / 4 * (10**2) * 20
    a_side = math.pi * 20 * 30 + math.pi * 10 * 20
    a_faces = math.pi / 4 * (20**2 + 10**2)
    mesh = _mesh(v_net, a_side + a_faces, (20.0, 20.0, 50.0))

    override = scad_metrics.build_geometry_override(request, mesh)

    assert override.v_net_mm3 == pytest.approx(v_net, rel=1e-6)
    assert override.v_gross_mm3 == pytest.approx(analytic.v_gross_mm3, rel=1e-6)
    assert override.a_inner_mm2 == 0.0
    assert override.a_outer_mm2 == pytest.approx(mesh.area_mm2, rel=1e-6)
    assert override.a_surf_mm2 == pytest.approx(mesh.area_mm2, rel=1e-6)


def test_build_override_hole_and_bore_inner_area() -> None:
    """a_inner = Σπ·d·L отверстий + расточка T2 (inner_steps)."""
    request = CalculateRequestDTO.model_validate(
        {
            **DOCX_CONTRACT,
            "features": [
                {
                    "type": "HOLE_ARRAY",
                    "count": 6,
                    "diameter": 11.0,
                    "depth": 20.0,
                    "tolerance": "IT11",
                }
            ],
        }
    )
    mesh = _mesh(500_000.0, 80_000.0, (160.0, 160.0, 80.0))
    override = scad_metrics.build_geometry_override(request, mesh)
    bore = math.pi * 72 * 35 + math.pi * 60 * 45  # inner_steps T2
    holes = 6 * math.pi * 11 * 20  # HOLE_ARRAY
    assert override.a_inner_mm2 == pytest.approx(bore + holes, rel=1e-6)
    assert override.a_outer_mm2 == pytest.approx(80_000.0 - bore - holes, rel=1e-6)


def test_build_override_rejects_net_above_gross() -> None:
    request = CalculateRequestDTO.model_validate({**T1_SHAFT, "cooperation": []})
    huge_mesh = _mesh(10_000_000.0, 1_000.0, (200.0, 200.0, 200.0))
    with pytest.raises(ValueError, match="v_gross"):
        scad_metrics.build_geometry_override(request, huge_mesh)


def test_build_override_rejects_empty_and_negative_area() -> None:
    request = CalculateRequestDTO.model_validate({**T1_SHAFT, "cooperation": []})
    empty = _mesh(0.0, 0.0, (0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="пуста"):
        scad_metrics.build_geometry_override(request, empty)
    # площадь сетки меньше a_inner отверстий → a_outer < 0
    with_holes = CalculateRequestDTO.model_validate(
        {
            **T1_SHAFT,
            "cooperation": [],
            "features": [
                {
                    "type": "HOLE_ARRAY",
                    "count": 6,
                    "diameter": 11.0,
                    "depth": 20.0,
                    "tolerance": "IT11",
                }
            ],
        }
    )
    tiny_area = _mesh(1_000.0, 1.0, (10.0, 10.0, 10.0))
    with pytest.raises(ValueError, match="площади"):
        scad_metrics.build_geometry_override(with_holes, tiny_area)


def test_validate_code_blocks_file_io_and_oversize() -> None:
    with pytest.raises(scad_compiler.ScadCompileError, match="import"):
        scad_compiler._validate_code('import("part.stl"); cube(1);')
    with pytest.raises(scad_compiler.ScadCompileError, match="include"):
        scad_compiler._validate_code("include <lib.scad>\ncube(1);")
    with pytest.raises(scad_compiler.ScadCompileError, match="лимит"):
        scad_compiler._validate_code("//" + "x" * (settings.scad_max_code_bytes + 1))


# --------------------------------------------------------- регрессия API


def test_request_without_scad_code_is_bitwise_same(client: TestClient) -> None:
    """Контракт стабильности: scad_code отсутствует или None — ответ совпадает."""
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    first = client.post(
        "/api/v1/calculate/25d-feature", json=DOCX_CONTRACT, headers=headers
    )
    second = client.post(
        "/api/v1/calculate/25d-feature",
        json={**DOCX_CONTRACT, "scad_code": None},
        headers=headers,
    )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


def test_calculate_scad_syntax_error_is_422(client: TestClient) -> None:
    if not scad_compiler.is_available():
        pytest.skip("OpenSCAD binary not found")
    token = _login(client)
    payload = {**T1_SHAFT, "scad_code": "this is ) not scad ;;"}
    response = client.post(
        "/api/v1/calculate/25d-feature",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_calculate_scad_unavailable_returns_clean_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Нет бинарника → понятная ошибка (422 расчёт / 503 превью), а не 500."""
    token = _login(client)
    monkeypatch.setattr(scad_compiler, "resolve_openscad_binary", lambda: None)
    payload = {**T1_SHAFT, "scad_code": "cube(1);"}

    calculate = client.post(
        "/api/v1/calculate/25d-feature",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    preview = client.post(
        "/api/v1/scad/preview",
        json={"scad_code": "cube(1);"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert calculate.status_code == 422
    assert preview.status_code == 503


# ------------------------------------------------------- /scad/preview


def test_preview_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/scad/preview", json={"scad_code": "cube(1);"})
    assert response.status_code == 401


def test_preview_rejects_oversized_code(client: TestClient) -> None:
    token = _login(client)
    response = client.post(
        "/api/v1/scad/preview",
        json={"scad_code": "x" * 100_001},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_capability_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/scad/capability")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["scad_available"], bool)
    assert body["scad_available"] == scad_compiler.is_available()


# ------------------------------------- интеграция с реальным бинарником

requires_openscad = pytest.mark.skipif(
    not scad_compiler.is_available(), reason="OpenSCAD binary not found"
)


@requires_openscad
def test_preview_cylinder_matches_analytics() -> None:
    """d=20 h=10: v_net = π/4·400·10 мм³ (допуск 0.5%), bbox = [20,20,10]."""
    code = "cylinder(h=10, d=20, $fn=96);"
    compiled, mesh = asyncio.run(scad_compiler.compile_and_measure(code))

    expected_mm3 = math.pi / 4 * 20**2 * 10
    assert mesh.volume_mm3 == pytest.approx(expected_mm3, rel=0.005)
    assert mesh.area_mm2 > 0
    assert mesh.extents_mm[0] == pytest.approx(20.0, rel=0.005)
    assert mesh.extents_mm[2] == pytest.approx(10.0, rel=0.005)
    assert compiled.stl_bytes[:5] == b"solid" or len(compiled.stl_bytes) > 84

    # Кэш LRU: повторная компиляция того же кода — тот же хэш без задержки
    again = asyncio.run(scad_compiler.compile_and_measure(code))
    assert again[0].code_hash == compiled.code_hash


@requires_openscad
def test_preview_api_returns_stl_and_metrics(client: TestClient) -> None:
    token = _login(client)
    response = client.post(
        "/api/v1/scad/preview",
        json={"scad_code": "cube([20, 10, 5]);"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert base64.b64decode(body["stl_base64"])
    assert body["bbox_mm"] == [20.0, 10.0, 5.0]
    assert body["v_net_cm3"] == pytest.approx(1.0, rel=0.005)
    assert body["compile_ms"] >= 0


@requires_openscad
def test_preview_empty_mesh_is_422(client: TestClient) -> None:
    token = _login(client)
    response = client.post(
        "/api/v1/scad/preview",
        json={"scad_code": "if (false) cube(1);"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@requires_openscad
def test_preview_oversized_stl_is_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Механизм лимита: сетка больше порога → 422 с подсказкой про $fn."""
    monkeypatch.setattr(settings, "scad_max_stl_mb", 1)
    token = _login(client)
    # sphere $fn=384 → ~920k треугольников ≈ 46 МБ > 1 МБ (быстро на Manifold)
    response = client.post(
        "/api/v1/scad/preview",
        json={"scad_code": "sphere(300, $fn = 384);"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "$fn" in response.json()["detail"]


@requires_openscad
def test_preview_timeout_is_killed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Тяжёлая булева модель + timeout 2 c → 422, процесс убит."""
    monkeypatch.setattr(settings, "openscad_timeout_s", 2)
    token = _login(client)
    heavy = (
        "difference() {\n"
        "  cube(60, center=true);\n"
        "  for (i = [0:400])\n"
        "    translate([cos(i) * 25, sin(i) * 25, 0])\n"
        "      cylinder(h=80, d=6, $fn=64, center=true);\n"
        "}\n"
    )
    response = client.post(
        "/api/v1/scad/preview",
        json={"scad_code": heavy},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert (
        "время" in response.json()["detail"] or "превысила" in response.json()["detail"]
    )


@requires_openscad
def test_calculate_with_scad_gross_matches_template_mode(client: TestClient) -> None:
    """v_gross аналитический в обоих режимах; v_net — из сетки (0.5%);
    маршрут/операции не меняются."""
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    template_mode = client.post(
        "/api/v1/calculate/25d-feature", json=T1_SHAFT, headers=headers
    )
    scad_mode = client.post(
        "/api/v1/calculate/25d-feature",
        json={**T1_SHAFT, "scad_code": T1_SHAFT_SCAD},
        headers=headers,
    )
    assert template_mode.status_code == scad_mode.status_code == 200
    plain, scad = template_mode.json(), scad_mode.json()

    # v_gross/заготовка/маршрут — идентичны (одна аналитика припусков)
    assert scad["v_gross_cm3"] == plain["v_gross_cm3"]
    assert scad["m_gross_kg"] == plain["m_gross_kg"]
    assert [op["code"] for op in scad["operations"]] == [
        op["code"] for op in plain["operations"]
    ]
    # v_net из сетки совпадает с аналитикой того же вала в пределах 0.5%
    assert scad["v_net_cm3"] == pytest.approx(plain["v_net_cm3"], rel=0.005)
    assert float(scad["price_per_part"]) == pytest.approx(
        float(plain["price_per_part"]), rel=0.02
    )


@requires_openscad
def test_ladder_compiles_scad_once(client: TestClient) -> None:
    """Лестница тиражей: ровно одна компиляция на запрос — miss LRU-кэша = 1
    (при ×7 подряд без кэша misses было бы 7)."""
    token = _login(client)
    scad_compiler._compile_cached.cache_clear()
    response = client.post(
        "/api/v1/calculate/25d-feature/ladder",
        json={**T1_SHAFT, "scad_code": T1_SHAFT_SCAD},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len({rung["batch_size"] for rung in response.json()}) == 7
    assert scad_compiler._compile_cached.cache_info().misses == 1


@requires_openscad
def test_scad_quote_snapshot_roundtrip(client: TestClient) -> None:
    """C5: сохранение SCAD-КП → переоткрытие → тот же расчёт
    (компиляция детерминирована, снапшот переносит scad_code)."""
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "Вал SCAD",
        "request": {**T1_SHAFT, "scad_code": T1_SHAFT_SCAD},
    }
    created = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert created.status_code == 201
    quote_id = created.json()["id"]
    assert created.json()["request"]["scad_code"] == T1_SHAFT_SCAD

    reopened = client.get(f"/api/v1/quotes/{quote_id}", headers=headers)
    assert reopened.status_code == 200
    detail = reopened.json()
    assert detail["request"]["scad_code"] == T1_SHAFT_SCAD
    # повторный расчёт того же запроса — те же числа
    recalculated = client.post(
        "/api/v1/calculate/25d-feature",
        json=detail["request"],
        headers=headers,
    )
    assert recalculated.status_code == 200
    assert recalculated.json() == detail["result"]
