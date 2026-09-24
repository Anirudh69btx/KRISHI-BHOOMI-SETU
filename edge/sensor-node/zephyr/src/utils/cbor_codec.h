#ifndef FLIP_UTILS_CBOR_CODEC_H_
#define FLIP_UTILS_CBOR_CODEC_H_

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

struct __attribute__((packed)) sensor_packet {
    uint32_t timestamp;      /* Unix epoch seconds */
    uint16_t seq_id;         /* Monotonic sequence number */
    uint8_t device_id[8];    /* MAC-derived 64-bit ID */
    float vwc;               /* Soil Volumetric Water Content % */
    float ec;                /* Electrical Conductivity dS/m */
    float temp_soil;         /* Soil Temperature °C */
    float temp_air;          /* Air Temperature °C */
    float rh;                /* Relative Humidity % */
    float leaf_wet;          /* Leaf Wetness 0.0 - 1.0 */
    float rain_mm;           /* Accumulated Rainfall mm */
    float par;               /* PAR Light µmol/m²/s */
    uint16_t battery_mv;     /* Battery Voltage mV */
    int8_t rssi;             /* LoRa RSSI dBm */
    int8_t snr;              /* LoRa SNR dB */
};

struct gateway_command {
    uint8_t cmd_type;        /* 1: config, 2: ota_trigger, 3: time_sync */
    uint32_t sleep_interval_sec;
    uint32_t timestamp;
    char ota_version[16];
};

int cbor_encode_sensor_packet(const struct sensor_packet *pkt, uint8_t *buf, size_t buf_size, size_t *out_len);
int cbor_decode_sensor_packet(const uint8_t *buf, size_t len, struct sensor_packet *pkt);
int cbor_decode_gateway_command(const uint8_t *buf, size_t len, struct gateway_command *cmd);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_UTILS_CBOR_CODEC_H_ */
