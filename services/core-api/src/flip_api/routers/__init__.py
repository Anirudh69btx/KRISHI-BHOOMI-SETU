"""FLIP Core API — routers package."""
from flip_api.routers.sensors import router as sensors_router
from flip_api.routers.farms import router as farms_router
from flip_api.routers.advisories import router as advisories_router
from flip_api.routers.disaster import router as disaster_router
from flip_api.routers.copilot import router as copilot_router
from flip_api.routers.auth import auth_router

__all__ = [
    "sensors_router",
    "farms_router",
    "advisories_router",
    "disaster_router",
    "copilot_router",
    "auth_router",
]
