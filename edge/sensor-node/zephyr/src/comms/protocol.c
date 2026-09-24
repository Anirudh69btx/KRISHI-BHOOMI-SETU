#include "protocol.h"
#include "../utils/crc16.h"
#include <string.h>

/* Consistent Overhead Byte Stuffing (COBS) Implementation */
size_t cobs_encode(const uint8_t *input, size_t length, uint8_t *output)
{
    size_t read_idx = 0;
    size_t write_idx = 1;
    size_t code_idx = 0;
    uint8_t code = 1;

    while (read_idx < length) {
        if (input[read_idx] == 0) {
            output[code_idx] = code;
            code_idx = write_idx++;
            code = 1;
            read_idx++;
        } else {
            output[write_idx++] = input[read_idx++];
            code++;
            if (code == 0xFF) {
                output[code_idx] = code;
                code_idx = write_idx++;
                code = 1;
            }
        }
    }
    output[code_idx] = code;
    return write_idx;
}

size_t cobs_decode(const uint8_t *input, size_t length, uint8_t *output)
{
    size_t read_idx = 0;
    size_t write_idx = 0;
    uint8_t code = 0xFF;
    uint8_t block = 0;

    while (read_idx < length) {
        if (block) {
            output[write_idx++] = input[read_idx++];
        } else {
            block = input[read_idx++];
            if (block && (code != 0xFF)) {
                output[write_idx++] = 0;
            }
            code = block;
            if (!block) break;
        }
        block--;
    }
    return write_idx;
}

int flip_protocol_frame(uint8_t msg_type, uint16_t seq_id, const uint8_t device_id[8],
                        const uint8_t *payload, uint8_t payload_len,
                        uint8_t *out_frame, size_t max_out_len, size_t *out_frame_len)
{
    size_t total_size = sizeof(struct flip_frame_header) + payload_len + sizeof(struct flip_frame_trailer);
    if (max_out_len < total_size) {
        return -1;
    }

    struct flip_frame_header hdr = {
        .magic = {FLIP_PROTO_MAGIC_1, FLIP_PROTO_MAGIC_2},
        .version = FLIP_PROTO_VERSION,
        .msg_type = msg_type,
        .seq_id = seq_id,
        .payload_len = payload_len,
    };
    if (device_id) {
        memcpy(hdr.device_id, device_id, 8);
    } else {
        memset(hdr.device_id, 0, 8);
    }

    uint8_t *p = out_frame;
    memcpy(p, &hdr, sizeof(hdr));
    p += sizeof(hdr);

    if (payload_len > 0 && payload != NULL) {
        memcpy(p, payload, payload_len);
        p += payload_len;
    }

    /* Compute CRC-16 across Header + Payload */
    uint16_t crc = crc16_ccitt(out_frame, sizeof(hdr) + payload_len);
    struct flip_frame_trailer trl = {.crc16 = crc};
    memcpy(p, &trl, sizeof(trl));
    p += sizeof(trl);

    *out_frame_len = total_size;
    return 0;
}

int flip_protocol_parse(const uint8_t *frame, size_t frame_len, uint8_t *msg_type,
                        uint16_t *seq_id, uint8_t device_id[8],
                        const uint8_t **payload, uint8_t *payload_len)
{
    if (frame_len < sizeof(struct flip_frame_header) + sizeof(struct flip_frame_trailer)) {
        return -1;
    }

    const struct flip_frame_header *hdr = (const struct flip_frame_header *)frame;
    if (hdr->magic[0] != FLIP_PROTO_MAGIC_1 || hdr->magic[1] != FLIP_PROTO_MAGIC_2) {
        return -2; /* Bad magic */
    }
    if (hdr->version != FLIP_PROTO_VERSION) {
        return -3; /* Version mismatch */
    }

    size_t expected_total = sizeof(struct flip_frame_header) + hdr->payload_len + sizeof(struct flip_frame_trailer);
    if (frame_len < expected_total) {
        return -4; /* Incomplete */
    }

    /* Verify CRC16 */
    uint16_t computed_crc = crc16_ccitt(frame, sizeof(struct flip_frame_header) + hdr->payload_len);
    const struct flip_frame_trailer *trl = 
        (const struct flip_frame_trailer *)(frame + sizeof(struct flip_frame_header) + hdr->payload_len);

    if (trl->crc16 != computed_crc) {
        return -5; /* CRC mismatch */
    }

    if (msg_type) *msg_type = hdr->msg_type;
    if (seq_id) *seq_id = hdr->seq_id;
    if (device_id) memcpy(device_id, hdr->device_id, 8);
    if (payload_len) *payload_len = hdr->payload_len;
    if (payload) *payload = frame + sizeof(struct flip_frame_header);

    return 0;
}

bool flip_protocol_is_ack_for(const uint8_t *frame, size_t frame_len, uint16_t expected_seq)
{
    uint8_t msg_type = 0;
    uint16_t seq = 0;
    int ret = flip_protocol_parse(frame, frame_len, &msg_type, &seq, NULL, NULL, NULL);
    if (ret == 0 && msg_type == FLIP_MSG_ACK && seq == expected_seq) {
        return true;
    }
    return false;
}
