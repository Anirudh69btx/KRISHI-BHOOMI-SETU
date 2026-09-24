"""
FLIP Core API — Strawberry GraphQL Schema (Federation-ready)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.scalars import JSON

# ---------- Scalar types --------------------------------------------------

@strawberry.type
class FarmType:
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    area_ha: float
    created_at: datetime
    updated_at: datetime

@strawberry.type
class SensorReadingType:
    id: uuid.UUID
    farm_id: uuid.UUID
    field_id: Optional[uuid.UUID]
    device_id: uuid.UUID
    sensor_type: str
    value: float
    unit: str
    quality_flag: str
    timestamp: datetime

@strawberry.type
class AdvisoryType:
    id: uuid.UUID
    farm_id: uuid.UUID
    advisory_type: str
    severity: str
    title: str
    body_text: str
    confidence_lo: float
    confidence_hi: float
    valid_from: datetime
    valid_until: Optional[datetime]
    created_at: datetime

@strawberry.type
class DisasterAlertType:
    id: uuid.UUID
    district_id: uuid.UUID
    alert_code: str
    severity: str
    title_en: str
    title_hi: str
    affected_area: Optional[JSON]
    issued_at: datetime
    expires_at: Optional[datetime]

# ---------- Query ---------------------------------------------------------

@strawberry.type
class Query:
    @strawberry.field(description="Fetch farms visible to the authenticated user")
    async def farms(self) -> list[FarmType]:
        # TODO: Wire to database session via Strawberry context
        return []

    @strawberry.field(description="Latest sensor readings for a farm")
    async def sensor_readings(
        self,
        farm_id: uuid.UUID,
        limit: int = 100,
    ) -> list[SensorReadingType]:
        return []

    @strawberry.field(description="Active advisories for a farm")
    async def advisories(
        self,
        farm_id: uuid.UUID,
    ) -> list[AdvisoryType]:
        return []

    @strawberry.field(description="Active disaster alerts for a district")
    async def disaster_alerts(
        self,
        district_id: uuid.UUID,
    ) -> list[DisasterAlertType]:
        return []

# ---------- Mutation ------------------------------------------------------

@strawberry.type
class Mutation:
    @strawberry.mutation(description="Acknowledge an advisory (farmer feedback loop)")
    async def acknowledge_advisory(
        self,
        advisory_id: uuid.UUID,
        action_taken: str,
    ) -> bool:
        # TODO: Persist to farmer_actions table and push to NATS
        return True

# ---------- Subscription --------------------------------------------------

@strawberry.type
class Subscription:
    @strawberry.subscription(description="Live sensor readings for a farm")
    async def sensor_stream(
        self, farm_id: uuid.UUID
    ):  # type: ignore[return]
        # TODO: Bridge from NATS JetStream subscription
        yield None  # placeholder

# ---------- Schema --------------------------------------------------------

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)

graphql_app = GraphQLRouter(schema, graphiql=True)
