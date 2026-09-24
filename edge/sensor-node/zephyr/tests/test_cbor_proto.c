#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "../src/utils/crc16.h"
#include "../src/utils/cbor_codec.h"
#include "../src/comms/protocol.h"

int main(void)
{
    printf("=== Testing Sensor Node CBOR Codec, CRC16 & Framing Protocol ===\n");

    /* 1. Test CRC-16 */
    const char *test_str = "123456789";
    uint16_t crc = crc16_ccitt((const uint8_t *)test_str, strlen(test_str));
    printf("CRC16 of '123456789': 0x%04X\n", crc);
    assert(crc == 0x29B1);
    printf("✅ CRC16 validated successfully.\n");

    /* 2. Test CBOR Encoding and Decoding */
    struct sensor_packet pkt_in = {
        .timestamp = 1700000000,
        .seq_id = 42,
        .device_id = {0xF0, 0xDE, 0xF1, 0x10, 0x00, 0x00, 0x01, 0x01},
        .vwc = 34.5f,
        .ec = 1.25f,
        .temp_soil = 25.4f,
        .temp_air = 31.2f,
        .rh = 68.5f,
        .leaf_wet = 0.45f,
        .rain_mm = 2.4f,
        .par = 950.0f,
        .battery_mv = 3280,
        .rssi = -75,
        .snr = 8,
    };

    uint8_t cbor_buf[128];
    size_t cbor_len = 0;
    int ret = cbor_encode_sensor_packet(&pkt_in, cbor_buf, sizeof(cbor_buf), &cbor_len);
    assert(ret == 0);
    printf("Encoded sensor packet into CBOR (%u bytes)\n", (unsigned int)cbor_len);
    assert(cbor_len > 0 && cbor_len < 100);

    struct sensor_packet pkt_out;
    ret = cbor_decode_sensor_packet(cbor_buf, cbor_len, &pkt_out);
    assert(ret == 0);
    assert(pkt_out.seq_id == 42);
    assert(pkt_out.battery_mv == 3280);
    assert(pkt_out.timestamp == 1700000000);
    printf("✅ CBOR encode and decode verified.\n");

    /* 3. Test LoRa Protocol Framing */
    uint8_t frame_buf[160];
    size_t frame_len = 0;
    ret = flip_protocol_frame(FLIP_MSG_TELEMETRY, pkt_in.seq_id, pkt_in.device_id, cbor_buf, (uint8_t)cbor_len,
                              frame_buf, sizeof(frame_buf), &frame_len);
    assert(ret == 0);

    uint8_t parsed_msg_type = 0;
    uint16_t parsed_seq_id = 0;
    uint8_t parsed_dev_id[8] = {0};
    const uint8_t *parsed_payload = NULL;
    uint8_t parsed_payload_len = 0;
    ret = flip_protocol_parse(frame_buf, frame_len, &parsed_msg_type, &parsed_seq_id,
                              parsed_dev_id, &parsed_payload, &parsed_payload_len);
    assert(ret == 0);
    assert(parsed_msg_type == FLIP_MSG_TELEMETRY);
    assert(parsed_seq_id == 42);
    assert(memcmp(parsed_dev_id, pkt_in.device_id, 8) == 0);
    assert(parsed_payload_len == cbor_len);
    assert(flip_protocol_is_ack_for(frame_buf, frame_len, 42) == false);
    printf("✅ LoRa Protocol Framing and CRC16 verification verified.\n");

    printf("=== All Sensor Node C Unit Tests Passed! ===\n");
    return 0;
}
