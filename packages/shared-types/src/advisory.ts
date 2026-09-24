import { z } from "zod";

export const AdvisorySeverityEnum = z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]);
export type AdvisorySeverity = z.infer<typeof AdvisorySeverityEnum>;

export const AdvisoryStatusEnum = z.enum([
  "ACTIVE",
  "ACKNOWLEDGED",
  "ACTIONED",
  "EXPIRED",
  "DISMISSED",
  "VERIFIED",
]);
export type AdvisoryStatus = z.infer<typeof AdvisoryStatusEnum>;

export const FarmerActionTypeEnum = z.enum([
  "SPRAY",
  "IRRIGATE",
  "FERTILIZE",
  "HARVEST",
  "SCOUT",
  "PRUNE",
  "SOW",
  "OTHER",
]);
export type FarmerActionType = z.infer<typeof FarmerActionTypeEnum>;

export const FarmerActionStatusEnum = z.enum([
  "PLANNED",
  "COMPLETED",
  "VERIFIED",
  "DISPUTED",
]);
export type FarmerActionStatus = z.infer<typeof FarmerActionStatusEnum>;

/**
 * Conformal Classification: outputs PredictionSet with coverage >= 95% (Master Requirement)
 * e.g. PredictionSet = {"Blight", "Unknown"}
 */
export const ConformalPredictionSetSchema = z.object({
  prediction_set: z.array(z.string()),
  confidence_scores: z.record(z.string(), z.number()).optional(),
  coverage_target: z.number().min(0).max(1).default(0.95),
  p_values: z.record(z.string(), z.number()).optional(),
});
export type ConformalPredictionSet = z.infer<typeof ConformalPredictionSetSchema>;

/**
 * Conformal Regression: outputs PredictionInterval for continuous quantities (yield, soil measurements)
 */
export const ConformalPredictionIntervalSchema = z.object({
  point_prediction: z.number(),
  lower_bound: z.number(),
  upper_bound: z.number(),
  coverage_target: z.number().min(0).max(1).default(0.95),
});
export type ConformalPredictionInterval = z.infer<typeof ConformalPredictionIntervalSchema>;

// Unified type alias for backward compatibility
export const ConformalPredictionSchema = z.object({
  prediction_set: z.array(z.string()).optional(),
  confidence_set: z.array(z.string()).default([]),
  coverage: z.number().min(0).max(1).default(0.95),
  coverage_target: z.number().min(0).max(1).default(0.95),
  interval: ConformalPredictionIntervalSchema.optional(),
});
export type ConformalPrediction = z.infer<typeof ConformalPredictionSchema>;

export const AdvisorySchema = z.object({
  id: z.string(),
  issued_at: z.string().datetime(),
  farm_id: z.string().uuid(),
  field_id: z.string().uuid().nullable().optional(),
  cycle_id: z.string().uuid().nullable().optional(),
  now_text: z.string(),
  next_text: z.string(),
  why_text: z.string(),
  // Conformal Classification Prediction Set
  prediction_set: z.array(z.string()).default([]),
  confidence_set: z.array(z.string()).default([]),
  coverage_target: z.number().default(0.95),
  coverage: z.number().default(0.95),
  risk_factors: z.record(z.unknown()).default({}),
  expires_at: z.string().datetime(),
  verification_due: z.string().datetime().nullable().optional(),
  status: AdvisoryStatusEnum.default("ACTIVE"),
  model_version: z.string(),
  metadata: z.record(z.unknown()).default({}),
});
export type Advisory = z.infer<typeof AdvisorySchema>;

export const FarmerActionSchema = z.object({
  id: z.string().uuid(),
  action_time: z.string().datetime(),
  advisory_id: z.string().nullable().optional(),
  farm_id: z.string().uuid(),
  field_id: z.string().uuid().nullable().optional(),
  farmer_id: z.string().uuid(),
  action_type: FarmerActionTypeEnum,
  inputs_applied: z.record(z.unknown()).default({}),
  notes: z.string().nullable().optional(),
  status: FarmerActionStatusEnum.default("COMPLETED"),
  verified_at: z.string().datetime().nullable().optional(),
  outcome_delta: z.record(z.unknown()).default({}),
  metadata: z.record(z.unknown()).default({}),
});
export type FarmerAction = z.infer<typeof FarmerActionSchema>;
