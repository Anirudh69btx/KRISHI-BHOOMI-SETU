#include "buffer_protocol.h"
#include "littlefs_manager.h"
#include "../comms/protocol.h"
#include "../comms/lora_sx1262.h"
#include "../utils/cbor_codec.h"
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(buffer_proto, LOG_LEVEL_INF);

int buffer_protocol_flush_batch(size_t max_packets)
{
    size_t flushed = 0;
    struct sensor_packet pkt;
    uint16_t seq_id = 0;
    uint8_t cbor_buf[128];
    uint8_t frame_buf[160];

    while (flushed < max_packets) {
        int ret = littlefs_read_next_buffered(&pkt, &seq_id);
        if (ret != 0) {
            /* No more buffered items */
            break;
        }

        size_t cbor_len = 0;
        ret = cbor_encode_sensor_packet(&pkt, cbor_buf, sizeof(cbor_buf), &cbor_len);
        if (ret != 0) {
            littlefs_delete_packet(seq_id);
            continue;
        }

        size_t frame_len = 0;
        ret = flip_protocol_frame(FLIP_MSG_BUFFER_BATCH, seq_id, pkt.device_id, cbor_buf, (uint8_t)cbor_len,
                                  frame_buf, sizeof(frame_buf), &frame_len);
        if (ret != 0) {
            littlefs_delete_packet(seq_id);
            continue;
        }

        ret = lora_sx1262_send(frame_buf, frame_len);
        if (ret == 0) {
            littlefs_delete_packet(seq_id);
            flushed++;
            k_sleep(K_MSEC(100)); /* Brief pause between bursts */
        } else {
            LOG_WRN("Failed to transmit buffered packet seq=%u, aborting batch", seq_id);
            break;
        }
    }

    if (flushed > 0) {
        LOG_INF("Flushed %zu buffered packets over LoRa", flushed);
    }
    return flushed;
}
