import { z } from "zod";
import { GeoPolygonSchema } from "./geo.js";

export const TwinEventTypeEnum = z.enum([
  "SENSOR_UPDATE",
  "IRRIGATION_START",
  "IRRIGATION_STOP",
  "HARVEST_EVENT",
  "PEST_DETECTED",
  "DISEASE_OUTBREAK",
  "SOIL_TEST_UPDATE",
  "BOUNDARY_EDIT",
  "CROP_STAGE_ADVANCE",
  "EQUIPMENT_TELEMETRY",
]);
export type TwinEventType = z.infer<typeof TwinEventTypeEnum>;

export const CropHealthIndexSchema = z.object({
  ndvi: z.number().min(0).max(1),
  canopy_cover_pct: z.number().min(0).max(100),
  stress_index: z.number().min(0).max(1),
  leaf_area_index: z.number().nonnegative(),
  last_updated: z.string().datetime(),
});
export type CropHealthIndex = z.infer<typeof CropHealthIndexSchema>;

export const DigitalTwinFieldStateSchema = z.object({
  field_id: z.string().uuid(),
  name: strOrNull(),
  boundary: GeoPolygonSchema,
  crop_type: z.string().nullable().optional(),
  sowing_date: z.string().datetime().nullable().optional(),
  current_stage: z.string().nullable().optional(),
  soil_moisture_vwc: z.number().nullable().optional(),
  soil_temperature_c: z.number().nullable().optional(),
  health_index: CropHealthIndexSchema.nullable().optional(),
  last_irrigated_at: z.string().datetime().nullable().optional(),
  active_alerts_count: z.number().int().default(0),
});
export type DigitalTwinFieldState = z.infer<typeof DigitalTwinFieldStateSchema>;

export const FarmDigitalTwinSchema = z.object({
  farm_id: z.string().uuid(),
  name: z.string(),
  latitude: z.number(),
  longitude: z.number(),
  crdt_clock: z.number().int().nonnegative().default(0),
  fields: z.array(DigitalTwinFieldStateSchema).default([]),
  recent_events_summary: z.record(z.unknown()).default({}),
  last_sync_at: z.string().datetime(),
});
export type FarmDigitalTwin = z.infer<typeof FarmDigitalTwinSchema>;

export const TwinEventSchema = z.object({
  id: z.string().uuid(),
  event_time: z.string().datetime(),
  farm_id: z.string().uuid(),
  field_id: z.string().uuid().nullable().optional(),
  event_type: TwinEventTypeEnum,
  actor_id: z.string().uuid().nullable().optional(),
  prev_state: z.record(z.unknown()).nullable().optional(),
  next_state: z.record(z.unknown()).nullable().optional(),
  crdt_clock: z.number().int().default(0),
  metadata: z.record(z.unknown()).default({}),
});
export type TwinEvent = z.infer<typeof TwinEventSchema>;

export const FarmSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid().nullable().optional(),
  name: z.string(),
  boundary: GeoPolygonSchema.nullable().optional(),
  latitude: z.number().nullable().optional(),
  longitude: z.number().nullable().optional(),
  area_acres: z.number().nullable().optional(),
  soil_type: z.string().nullable().optional(),
  irrigation_source: z.string().nullable().optional(),
  metadata: z.record(z.unknown()).default({}),
});
export type Farm = z.infer<typeof FarmSchema>;

function strOrNull() {
  return z.string().nullable().optional();
}

