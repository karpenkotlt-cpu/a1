from fastapi import APIRouter

from app.api.v1 import (
    auth,
    calculate,
    health,
    master_data,
    materials,
    quotes,
    scad,
    tool_baskets,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(materials.router)
api_router.include_router(calculate.router)
api_router.include_router(scad.router)
api_router.include_router(quotes.router)
api_router.include_router(tool_baskets.router)
api_router.include_router(master_data.router)
