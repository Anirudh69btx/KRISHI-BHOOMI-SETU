#include "cbor_codec.h"
#include <string.h>

/* Minimal CBOR writer helpers */
static void write_uint(uint8_t **p, uint64_t val, uint8_t major)
{
    if (val < 24) {
        *(*p)++ = (major << 5) | (uint8_t)val;
    } else if (val <= 0xFF) {
        *(*p)++ = (major << 5) | 24;
        *(*p)++ = (uint8_t)val;
    } else if (val <= 0xFFFF) {
        *(*p)++ = (major << 5) | 25;
        *(*p)++ = (uint8_t)(val >> 8);
        *(*p)++ = (uint8_t)val;
    } else if (val <= 0xFFFFFFFF) {
        *(*p)++ = (major << 5) | 26;
        *(*p)++ = (uint8_t)(val >> 24);
        *(*p)++ = (uint8_t)(val >> 16);
        *(*p)++ = (uint8_t)(val >> 8);
        *(*p)++ = (uint8_t)val;
    }
}

static void write_float(uint8_t **p, float val)
{
    *(*p)++ = 0xFA; /* Major 7, additional 26 = 32-bit single precision IEEE 754 */
    uint32_t raw;
    memcpy(&raw, &val, sizeof(float));
    *(*p)++ = (uint8_t)(raw >> 24);
    *(*p)++ = (uint8_t)(raw >> 16);
    *(*p)++ = (uint8_t)(raw >> 8);
    *(*p)++ = (uint8_t)raw;
}

static void write_bytes(uint8_t **p, const uint8_t *data, size_t len)
{
    write_uint(p, len, 2); /* Major 2: byte string */
    memcpy(*p, data, len);
    *p += len;
}

static void write_int(uint8_t **p, int32_t val)
{
    if (val >= 0) {
        write_uint(p, (uint64_t)val, 0); /* Major 0 */
    } else {
        write_uint(p, (uint64_t)(-1 - val), 1); /* Major 1: negative int */
    }
}

int cbor_encode_sensor_packet(const struct sensor_packet *pkt, uint8_t *buf, size_t buf_size, size_t *out_len)
{
    if (!pkt || !buf || buf_size < 96) {
        return -1;
    }

    uint8_t *p = buf;

    /* CBOR map with 14 items */
    write_uint(&p, 14, 5); /* Major 5: map */

    /* 0: timestamp */
    write_uint(&p, 0, 0);
    write_uint(&p, pkt->timestamp, 0);

    /* 1: seq_id */
    write_uint(&p, 1, 0);
    write_uint(&p, pkt->seq_id, 0);

    /* 2: device_id */
    write_uint(&p, 2, 0);
    write_bytes(&p, pkt->device_id, 8);

    /* 3: vwc */
    write_uint(&p, 3, 0);
    write_float(&p, pkt->vwc);

    /* 4: ec */
    write_uint(&p, 4, 0);
    write_float(&p, pkt->ec);

    /* 5: temp_soil */
    write_uint(&p, 5, 0);
    write_float(&p, pkt->temp_soil);

    /* 6: temp_air */
    write_uint(&p, 6, 0);
    write_float(&p, pkt->temp_air);

    /* 7: rh */
    write_uint(&p, 7, 0);
    write_float(&p, pkt->rh);

    /* 8: leaf_wet */
    write_uint(&p, 8, 0);
    write_float(&p, pkt->leaf_wet);

    /* 9: rain_mm */
    write_uint(&p, 9, 0);
    write_float(&p, pkt->rain_mm);

    /* 10: par */
    write_uint(&p, 10, 0);
    write_float(&p, pkt->par);

    /* 11: battery_mv */
    write_uint(&p, 11, 0);
    write_uint(&p, pkt->battery_mv, 0);

    /* 12: rssi */
    write_uint(&p, 12, 0);
    write_int(&p, pkt->rssi);

    /* 13: snr */
    write_uint(&p, 13, 0);
    write_int(&p, pkt->snr);

    *out_len = (size_t)(p - buf);
    return 0;
}

static uint64_t read_uint(const uint8_t **p)
{
    uint8_t byte = *(*p)++;
    uint8_t add = byte & 0x1F;
    if (add < 24) {
        return add;
    } else if (add == 24) {
        return *(*p)++;
    } else if (add == 25) {
        uint64_t val = ((uint64_t)(*p)[0] << 8) | (*p)[1];
        *p += 2;
        return val;
    } else if (add == 26) {
        uint64_t val = ((uint64_t)(*p)[0] << 24) | ((uint64_t)(*p)[1] << 16) | ((uint64_t)(*p)[2] << 8) | (*p)[3];
        *p += 4;
        return val;
    }
    return 0;
}

static int32_t read_int(const uint8_t **p)
{
    uint8_t major = (**p) >> 5;
    uint64_t u = read_uint(p);
    if (major == 1) {
        return -(int32_t)(u + 1);
    }
    return (int32_t)u;
}

int cbor_decode_sensor_packet(const uint8_t *buf, size_t len, struct sensor_packet *pkt)
{
    if (!buf || !pkt || len < 10) {
        return -1;
    }

    memset(pkt, 0, sizeof(*pkt));
    const uint8_t *p = buf;
    const uint8_t *end = buf + len;

    /* Skip map header */
    read_uint(&p);

    /* Standard map unpack */
    while (p < end) {
        uint64_t key = read_uint(&p);
        if (key > 13) continue;

        switch (key) {
        case 0: /* timestamp */
            pkt->timestamp = (uint32_t)read_uint(&p);
            break;
        case 1: /* seq_id */
            pkt->seq_id = (uint16_t)read_uint(&p);
            break;
        case 2: /* device_id */
            if (*p == 0x48) { /* byte string len 8 */
                p++;
                memcpy(pkt->device_id, p, 8);
                p += 8;
            } else {
                read_uint(&p);
            }
            break;
        case 3: /* vwc */
        case 4: /* ec */
        case 5: /* temp_soil */
        case 6: /* temp_air */
        case 7: /* rh */
        case 8: /* leaf_wet */
        case 9: /* rain_mm */
        case 10: /* par */
            if (*p == 0xFA) {
                p++;
                uint32_t raw = ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
                float fval;
                memcpy(&fval, &raw, sizeof(float));
                p += 4;
                if (key == 3) pkt->vwc = fval;
                else if (key == 4) pkt->ec = fval;
                else if (key == 5) pkt->temp_soil = fval;
                else if (key == 6) pkt->temp_air = fval;
                else if (key == 7) pkt->rh = fval;
                else if (key == 8) pkt->leaf_wet = fval;
                else if (key == 9) pkt->rain_mm = fval;
                else if (key == 10) pkt->par = fval;
            } else { p++; }
            break;
        case 11: /* battery_mv */
            pkt->battery_mv = (uint16_t)read_uint(&p);
            break;
        case 12: /* rssi */
            pkt->rssi = (int8_t)read_int(&p);
            break;
        case 13: /* snr */
            pkt->snr = (int8_t)read_int(&p);
            break;
        default:
            break;
        }
    }

    return 0;
}

int cbor_decode_gateway_command(const uint8_t *buf, size_t len, struct gateway_command *cmd)
{
    if (!buf || !cmd || len < 4) {
        return -1;
    }

    memset(cmd, 0, sizeof(*cmd));
    const uint8_t *p = buf;
    const uint8_t *end = buf + len;

    /* Skip map header */
    read_uint(&p);

    while (p < end) {
        uint64_t key = read_uint(&p);
        switch (key) {
        case 1: /* cmd_type */
            cmd->cmd_type = (uint8_t)read_uint(&p);
            break;
        case 2: /* sleep_interval_sec */
            cmd->sleep_interval_sec = (uint32_t)read_uint(&p);
            break;
        case 3: /* timestamp */
            cmd->timestamp = (uint32_t)read_uint(&p);
            break;
        case 4: /* ota_version (text string) */
            if ((*p >> 5) == 3) { /* text string */
                uint64_t slen = read_uint(&p);
                size_t copy_len = (slen < sizeof(cmd->ota_version) - 1) ? slen : (sizeof(cmd->ota_version) - 1);
                memcpy(cmd->ota_version, p, copy_len);
                cmd->ota_version[copy_len] = '\0';
                p += slen;
            } else {
                read_uint(&p);
            }
            break;
        default:
            read_uint(&p);
            break;
        }
    }
    return 0;
}
