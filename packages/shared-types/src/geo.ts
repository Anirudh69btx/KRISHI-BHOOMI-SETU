import { z } from "zod";

export const PositionSchema = z.tuple([z.number(), z.number()]);
export type Position = z.infer<typeof PositionSchema>;

export const BoundingBoxSchema = z.tuple([z.number(), z.number(), z.number(), z.number()]);
export type BoundingBox = z.infer<typeof BoundingBoxSchema>;

export const GeoPointSchema = z.object({
  type: z.literal("Point"),
  coordinates: PositionSchema,
});
export type GeoPoint = z.infer<typeof GeoPointSchema>;

export const GeoPolygonSchema = z.object({
  type: z.literal("Polygon"),
  coordinates: z.array(z.array(PositionSchema)),
});
export type GeoPolygon = z.infer<typeof GeoPolygonSchema>;

export const GeoMultiPolygonSchema = z.object({
  type: z.literal("MultiPolygon"),
  coordinates: z.array(z.array(z.array(PositionSchema))),
});
export type GeoMultiPolygon = z.infer<typeof GeoMultiPolygonSchema>;

export const GeoFeatureSchema = z.object({
  type: z.literal("Feature"),
  id: z.string().optional(),
  geometry: z.union([GeoPointSchema, GeoPolygonSchema, GeoMultiPolygonSchema]),
  properties: z.record(z.unknown()),
});
export type GeoFeature = z.infer<typeof GeoFeatureSchema>;

export const GeoFeatureCollectionSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(GeoFeatureSchema),
});
export type GeoFeatureCollection = z.infer<typeof GeoFeatureCollectionSchema>;
