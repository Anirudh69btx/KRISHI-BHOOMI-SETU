import { z } from "zod";
import { GeoPolygonSchema } from "./geo.js";

export const DisasterEventTypeEnum = z.enum([
  "HEATWAVE",
  "FLASH_FLOOD",
  "HAILSTORM",
  "LOCUST_SWARM",
  "PEST_OUTBREAK",
  "CYCLONE",
  "DROUGHT",
  "FROST",
]);
export type DisasterEventType = z.infer<typeof DisasterEventTypeEnum>;

export const DisasterSeverityEnum = z.enum([
  "ADVISORY",
  "WATCH",
  "WARNING",
  "EMERGENCY",
]);
export type DisasterSeverity = z.infer<typeof DisasterSeverityEnum>;

export const DisasterSourceEnum = z.enum([
  "IMD",
  "NDMA",
  "SATELLITE",
  "LOCAL_SENSOR",
  "COMMUNITY",
  "AI_EARLY_WARNING",
]);
export type DisasterSource = z.infer<typeof DisasterSourceEnum>;

export const DisasterStatusEnum = z.enum([
  "ACTIVE",
  "CANCELLED",
  "EXPIRED",
]);
export type DisasterStatus = z.infer<typeof DisasterStatusEnum>;

export const DisasterMessageTemplateSchema = z.object({
  title_en: z.string(),
  title_hi: z.string(),
  body_en: z.string(),
  body_hi: z.string(),
  audio_url_hi: z.string().optional(),
  action_steps_en: z.array(z.string()).default([]),
  action_steps_hi: z.array(z.string()).default([]),
});
export type DisasterMessageTemplate = z.infer<typeof DisasterMessageTemplateSchema>;

export const DisasterAlertSchema = z.object({
  id: z.string(),
  issued_at: z.string().datetime(),
  event_type: DisasterEventTypeEnum,
  severity: DisasterSeverityEnum,
  geometry: GeoPolygonSchema,
  expires_at: z.string().datetime(),
  message_template: DisasterMessageTemplateSchema,
  source: DisasterSourceEnum,
  status: DisasterStatusEnum.default("ACTIVE"),
  sirens_triggered: z.boolean().default(false),
  ivr_dispatched: z.boolean().default(false),
  metadata: z.record(z.unknown()).default({}),
});
export type DisasterAlert = z.infer<typeof DisasterAlertSchema>;
