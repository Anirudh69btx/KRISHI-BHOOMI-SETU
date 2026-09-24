import { z } from "zod";

/**
 * Yjs CRDT Synchronization Protocol Types for FLIP Digital Twin
 * ADR-003: Event Sourcing & Offline-First CRDT Local-First Sync
 */

export const CRDTSyncMessageTypeEnum = z.enum([
  "SYNC_STEP_1",    // Client/Server sends State Vector
  "SYNC_STEP_2",    // Missing updates sent based on State Vector
  "UPDATE",         // Incremental document update
  "AWARENESS",      // Farmer/Agronomist active presence
]);
export type CRDTSyncMessageType = z.infer<typeof CRDTSyncMessageTypeEnum>;

export const VectorClockSchema = z.record(z.string(), z.number().int().nonnegative());
export type VectorClock = z.infer<typeof VectorClockSchema>;

export const YjsDocUpdateSchema = z.object({
  farm_id: z.string().uuid(),
  field_id: z.string().uuid().optional(),
  client_id: z.number().int().nonnegative(),
  clock: z.number().int().nonnegative(),
  vector_clock: VectorClockSchema.optional(),
  // Base64-encoded Uint8Array of Y.encodeStateAsUpdate(ydoc)
  update_base64: z.string(),
  timestamp: z.string().datetime(),
});
export type YjsDocUpdate = z.infer<typeof YjsDocUpdateSchema>;

export const YjsSyncMessageSchema = z.object({
  type: CRDTSyncMessageTypeEnum,
  farm_id: z.string().uuid(),
  sender_id: z.string(),
  // Base64 encoded payload for the corresponding Yjs sync step
  payload_base64: z.string(),
  clock: z.number().int().nonnegative(),
  timestamp: z.string().datetime(),
});
export type YjsSyncMessage = z.infer<typeof YjsSyncMessageSchema>;

export const FarmTwinCRDTStateSchema = z.object({
  farm_id: z.string().uuid(),
  version: z.number().int().nonnegative(),
  root_doc_id: z.string(),
  last_snapshot_clock: z.number().int().nonnegative(),
  active_peers: z.array(z.string()).default([]),
  updated_at: z.string().datetime(),
});
export type FarmTwinCRDTState = z.infer<typeof FarmTwinCRDTStateSchema>;
