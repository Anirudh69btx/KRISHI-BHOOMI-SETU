import { z } from "zod";

export const SensorTypeEnum = z.enum([
  "VWC",           // Volumetric Water Content (%)
  "EC",            // Electrical Conductivity (dS/m)
  "TEMP_SOIL",     // Soil Temperature (°C)
  "TEMP_AIR",      // Air Temperature (°C)
  "HUMIDITY",      // Relative Humidity (%RH)
  "LEAF_WETNESS",  // Leaf Wetness (hours)
  "LIGHT_PAR",     // Photosynthetically Active Radiation (µmol/m²/s)
  "WIND_SPEED",    // Wind Speed (m/s)
  "WIND_DIR",      // Wind Direction (degrees)
  "RAIN_GAUGE",    // Rainfall (mm)
  "PRESSURE_ATM",  // Atmospheric Pressure (hPa)
  "CO2",           // Carbon Dioxide (ppm)
  "NDVI",          // Normalized Difference Veg Index (0-1)
  "PH",            // Soil pH (0-14)
  "NPK_N",         // Nitrogen (mg/kg)
  "NPK_P",         // Phosphorus (mg/kg)
  "NPK_K",         // Potassium (mg/kg)
]);
export type SensorType = z.infer<typeof SensorTypeEnum>;

export const QualityFlagEnum = z.enum([
  "VALID",
  "SUSPECT",
  "OUT_OF_BOUNDS",
  "CALIBRATED",
  "INTERPOLATED",
  "RAW",
]);
export type QualityFlag = z.infer<typeof QualityFlagEnum>;

export const SensorMetadataSchema = z.object({
  battery_v: z.number().optional(),
  rssi_dbm: z.number().optional(),
  snr: z.number().optional(),
  firmware: z.string().optional(),
  temperature_internal: z.number().optional(),
  retransmission_count: z.number().optional(),
}).passthrough();
export type SensorMetadata = z.infer<typeof SensorMetadataSchema>;

export const SensorReadingSchema = z.object({
  time: z.string().datetime(),
  farm_id: z.string().uuid(),
  field_id: z.string().uuid().nullable().optional(),
  device_id: z.string().uuid(),
  sensor_type: SensorTypeEnum,
  value: z.number(),
  raw_value: z.number().optional(),
  quality_flag: QualityFlagEnum.default("VALID"),
  metadata: SensorMetadataSchema.default({}),
});
export type SensorReading = z.infer<typeof SensorReadingSchema>;

export const SensorBatchPayloadSchema = z.object({
  device_id: z.string().uuid(),
  farm_id: z.string().uuid(),
  field_id: z.string().uuid().optional(),
  timestamp: z.string().datetime(),
  batch: z.number().int().positive().optional(),
  readings: z.array(
    z.object({
      sensor_type: SensorTypeEnum,
      value: z.number(),
      unit: z.string(),
      raw_value: z.number().optional(),
    })
  ),
  metadata: SensorMetadataSchema.default({}),
});
export type SensorBatchPayload = z.infer<typeof SensorBatchPayloadSchema>;

export const SensorAggregateWindowSchema = z.object({
  bucket: z.string().datetime(),
  sensor_type: SensorTypeEnum,
  avg_val: z.number(),
  min_val: z.number(),
  max_val: z.number(),
  reading_count: z.number().int(),
  valid_count: z.number().int(),
});
export type SensorAggregateWindow = z.infer<typeof SensorAggregateWindowSchema>;
