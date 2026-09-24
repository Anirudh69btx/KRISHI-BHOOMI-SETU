#ifndef FLIP_COMMS_PROTOCOL_H_
#define FLIP_COMMS_PROTOCOL_H_

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Magic bytes: 'F', 'L' = 0x46, 0x4C */
#define FLIP_PROTO_MAGIC_1 0x46
#define FLIP_PROTO_MAGIC_2 0x4C
#define FLIP_PROTO_VERSION 0x01

#define FLIP_MAX_FRAG_PAYLOAD 190
#define FLIP_MAX_FRAME_SIZE   255

enum flip_msg_type {
    FLIP_MSG_TELEMETRY    = 0x01,
    FLIP_MSG_ACK          = 0x02,
    FLIP_MSG_NACK         = 0x03,
    FLIP_MSG_TIME_SYNC    = 0x04,
    FLIP_MSG_CONFIG       = 0x05,
    FLIP_MSG_OTA_TRIGGER  = 0x06,
    FLIP_MSG_BUFFER_BATCH = 0x07,
    FLIP_MSG_FRAGMENT     = 0x08,
};

struct __attribute__((packed)) flip_frame_header {
    uint8_t magic[2];      /* 0x46, 0x4C */
    uint8_t version;       /* 0x01 */
    uint8_t msg_type;      /* enum flip_msg_type */
    uint16_t seq_id;       /* Monotonic sequence id */
    uint8_t device_id[8];  /* 8-byte device EUI/MAC */
    uint8_t payload_len;   /* Length of payload */
};

struct __attribute__((packed)) flip_frame_trailer {
    uint16_t crc16;        /* CRC-16-CCITT across header + payload */
};

/* Consistent Overhead Byte Stuffing (COBS) for zero-delimited framing */
size_t cobs_encode(const uint8_t *input, size_t length, uint8_t *output);
size_t cobs_decode(const uint8_t *input, size_t length, uint8_t *output);

/* Framing API */
int flip_protocol_frame(uint8_t msg_type, uint16_t seq_id, const uint8_t device_id[8],
                        const uint8_t *payload, uint8_t payload_len,
                        uint8_t *out_frame, size_t max_out_len, size_t *out_frame_len);

int flip_protocol_parse(const uint8_t *frame, size_t frame_len, uint8_t *msg_type,
                        uint16_t *seq_id, uint8_t device_id[8],
                        const uint8_t **payload, uint8_t *payload_len);

bool flip_protocol_is_ack_for(const uint8_t *frame, size_t frame_len, uint16_t expected_seq);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_COMMS_PROTOCOL_H_ */
