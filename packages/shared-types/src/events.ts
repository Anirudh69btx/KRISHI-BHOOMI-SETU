import { z } from "zod";
import { SensorReadingSchema } from "./sensor.js";
import { AdvisorySchema } from "./advisory.js";
import { TwinEventSchema } from "./twin.js";
import { DisasterAlertSchema } from "./disaster.js";

/**
 * Canonical NATS Subject builder functions for FLIP v3.0 (Master Requirement)
 */
export const NatsSubjects = {
  farmSensorRaw: (farmId: string) => `farm.${farmId}.sensor.raw` as const,
  farmAdvisoryGenerated: (farmId: string) => `farm.${farmId}.advisory.generated` as const,
  farmTwinUpdated: (farmId: string) => `farm.${farmId}.twin.updated` as const,
  regionOutbreakDetected: (districtId: string) => `region.${districtId}.outbreak.detected` as const,
  modelRegistryUpdated: () => "model.registry.updated" as const,
} as const;

/**
 * Canonical CloudEvents v1.0 Envelope Schema (Master Requirement)
 */
export const CloudEventSchema = z.object({
  specversion: z.literal("1.0").default("1.0"),
  id: z.string().uuid(),
  type: z.string(),
  source: z.string(),
  subject: z.string(),
  time: z.string().datetime(),
  datacontenttype: z.literal("application/json").default("application/json"),
  data: z.unknown(),
});
export type CloudEvent<T = unknown> = z.infer<typeof CloudEventSchema> & {
  data: T;
};

// Backwards-compatible alias for existing imports
export const EventEnvelopeSchema = CloudEventSchema;
export type EventEnvelope<T = unknown> = CloudEvent<T>;

/**
 * Canonical Event Schemas bound to canonical subjects
 */
export const SensorRawEventSchema = CloudEventSchema.extend({
  type: z.literal("farm.sensor.raw"),
  data: SensorReadingSchema,
});
export type SensorRawEvent = z.infer<typeof SensorRawEventSchema>;

export const AdvisoryGeneratedEventSchema = CloudEventSchema.extend({
  type: z.literal("farm.advisory.generated"),
  data: AdvisorySchema,
});
export type AdvisoryGeneratedEvent = z.infer<typeof AdvisoryGeneratedEventSchema>;

export const TwinUpdatedEventSchema = CloudEventSchema.extend({
  type: z.literal("farm.twin.updated"),
  data: TwinEventSchema,
});
export type TwinUpdatedEvent = z.infer<typeof TwinUpdatedEventSchema>;

export const OutbreakDetectedEventSchema = CloudEventSchema.extend({
  type: z.literal("region.outbreak.detected"),
  data: DisasterAlertSchema,
});
export type OutbreakDetectedEvent = z.infer<typeof OutbreakDetectedEventSchema>;

export const ModelRegistryUpdatedEventSchema = CloudEventSchema.extend({
  type: z.literal("model.registry.updated"),
  data: z.object({
    model_name: z.string(),
    model_version: z.string(),
    artifact_uri: z.string(),
    metrics: z.record(z.number()),
    coverage_target: z.number().default(0.95),
  }),
});
export type ModelRegistryUpdatedEvent = z.infer<typeof ModelRegistryUpdatedEventSchema>;
