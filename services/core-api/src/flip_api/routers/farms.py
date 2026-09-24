"""
FLIP v3.0 — Core API REST Routers
Farms router: CRUD for farm profiles, boundary GeoJSON, digital twin state.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from flip_api.auth.keycloak import get_current_user
from flip_api.database import get_session

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/farms", tags=["farms"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class FarmCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    area_hectares: float = Field(..., gt=0)
    soil_type: Optional[str] = None
    primary_crop: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: str = "IN"
    boundary_geojson: Optional[dict[str, Any]] = None


class FarmResponse(BaseModel):
    id: str
    name: str
    area_hectares: float
    soil_type: Optional[str]
    primary_crop: Optional[str]
    district: Optional[str]
    state: Optional[str]
    country: str
    is_active: bool
    created_at: str
    updated_at: str


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    area_hectares: Optional[float] = None
    soil_type: Optional[str] = None
    primary_crop: Optional[str] = None
    boundary_geojson: Optional[dict[str, Any]] = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[FarmResponse],
    summary="List farms for current farmer",
)
async def list_farms(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    farmer_id = current_user.get("farmer_id")
    if not farmer_id:
        # Admins can see all farms; regular users only see their own
        roles = current_user.get("realm_access", {}).get("roles", [])
        if "flip-admin" not in roles:
            raise HTTPException(status_code=403, detail="No farmer profile found")

    query = text("""
        SELECT
            id::text, name, area_hectares, soil_type, primary_crop,
            district, state, country, is_active,
            created_at::text, updated_at::text
        FROM farms
        WHERE (:farmer_id::uuid IS NULL OR farmer_id = :farmer_id::uuid)
          AND is_active = true
        ORDER BY created_at DESC
        LIMIT 100
    """)

    result = await session.execute(query, {"farmer_id": farmer_id})
    return [dict(r) for r in result.mappings().all()]


@router.post(
    "/",
    response_model=FarmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new farm",
)
async def create_farm(
    farm: FarmCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    farmer_id = current_user.get("farmer_id")
    if not farmer_id:
        raise HTTPException(status_code=403, detail="Only farmers can create farms")

    farm_id = uuid.uuid4()

    # Insert farm record
    await session.execute(
        text("""
            INSERT INTO farms
                (id, farmer_id, name, area_hectares, soil_type, primary_crop,
                 district, state, country, is_active)
            VALUES
                (:id, :farmer_id, :name, :area_hectares, :soil_type, :primary_crop,
                 :district, :state, :country, true)
        """),
        {
            "id": str(farm_id),
            "farmer_id": farmer_id,
            "name": farm.name,
            "area_hectares": farm.area_hectares,
            "soil_type": farm.soil_type,
            "primary_crop": farm.primary_crop,
            "district": farm.district,
            "state": farm.state,
            "country": farm.country,
        },
    )

    # Insert boundary if provided
    if farm.boundary_geojson:
        import json
        await session.execute(
            text("""
                INSERT INTO farm_boundaries (farm_id, boundary, area_calculated_ha)
                VALUES (:farm_id, ST_GeomFromGeoJSON(:geojson), :area)
                ON CONFLICT (farm_id) DO UPDATE
                    SET boundary = EXCLUDED.boundary,
                        area_calculated_ha = EXCLUDED.area_calculated_ha,
                        updated_at = now()
            """),
            {
                "farm_id": str(farm_id),
                "geojson": json.dumps(farm.boundary_geojson),
                "area": farm.area_hectares,
            },
        )

    await session.commit()
    log.info("farm_created", farm_id=str(farm_id), farmer_id=farmer_id)

    # Return created farm
    result = await session.execute(
        text("""
            SELECT id::text, name, area_hectares, soil_type, primary_crop,
                   district, state, country, is_active,
                   created_at::text, updated_at::text
            FROM farms WHERE id = :id
        """),
        {"id": str(farm_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=500, detail="Farm creation failed")
    return dict(row)


@router.get(
    "/{farm_id}",
    response_model=FarmResponse,
    summary="Get farm details",
)
async def get_farm(
    farm_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await session.execute(
        text("""
            SELECT id::text, name, area_hectares, soil_type, primary_crop,
                   district, state, country, is_active,
                   created_at::text, updated_at::text
            FROM farms
            WHERE id = :id AND is_active = true
        """),
        {"id": str(farm_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Farm not found")
    return dict(row)


@router.get(
    "/{farm_id}/twin",
    summary="Get digital twin state for a farm",
)
async def get_farm_twin(
    farm_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await session.execute(
        text("""
            SELECT
                dt.farm_id::text,
                dt.twin_type,
                dt.state_json,
                dt.health_score,
                dt.confidence,
                dt.valid_from::text,
                dt.computed_at::text
            FROM digital_twins dt
            WHERE dt.farm_id = :farm_id
            ORDER BY dt.computed_at DESC
            LIMIT 1
        """),
        {"farm_id": str(farm_id)},
    )
    row = result.mappings().first()
    if not row:
        return {
            "farm_id": str(farm_id),
            "twin_type": "crop",
            "state_json": {},
            "health_score": None,
            "confidence": None,
            "message": "Digital twin not yet computed",
        }
    return dict(row)


@router.get(
    "/{farm_id}/boundary",
    summary="Get farm boundary as GeoJSON",
)
async def get_farm_boundary(
    farm_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await session.execute(
        text("""
            SELECT
                farm_id::text,
                ST_AsGeoJSON(boundary)::json AS geometry,
                area_calculated_ha
            FROM farm_boundaries
            WHERE farm_id = :farm_id
        """),
        {"farm_id": str(farm_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Boundary not found")

    return {
        "type": "Feature",
        "properties": {
            "farm_id": row["farm_id"],
            "area_ha": row["area_calculated_ha"],
        },
        "geometry": row["geometry"],
    }
