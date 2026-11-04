import base64
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import require_roles
from app.db.models import User
from app.domain.enums import UserRole
from app.services import scad_compiler

router = APIRouter(prefix="/scad", tags=["scad"])


class ScadPreviewRequest(BaseModel):
    scad_code: str = Field(min_length=1, max_length=100_000)


class ScadPreviewResponse(BaseModel):
    """Лёгкое превью: STL для вьюпорта + метрики; расчёт — отдельно."""

    stl_base64: str
    bbox_mm: list[float]
    v_net_cm3: float
    compile_ms: int


@router.post("/preview")
async def preview_scad(
    payload: ScadPreviewRequest,
    user: Annotated[
        User,
        Depends(require_roles(UserRole.MANAGER, UserRole.TECHNOLOGIST, UserRole.ADMIN)),
    ],
) -> ScadPreviewResponse:
    try:
        compiled, mesh = await scad_compiler.compile_and_measure(payload.scad_code)
    except scad_compiler.ScadUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except scad_compiler.ScadCompileError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return ScadPreviewResponse(
        stl_base64=base64.b64encode(compiled.stl_bytes).decode("ascii"),
        bbox_mm=[round(axis, 3) for axis in mesh.extents_mm],
        v_net_cm3=round(mesh.volume_mm3 / 1000.0, 3),
        compile_ms=compiled.compile_ms,
    )


@router.get("/capability")
async def scad_capability() -> dict[str, bool]:
    """Kill-switch + наличие бинарника: фронт прячет SCAD-режимы, если false."""
    return {"scad_available": scad_compiler.is_available()}
