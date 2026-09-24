#include "mqtt_sn.h"
#include <string.h>

int mqtt_sn_encode_publish(uint16_t topic_id, uint16_t msg_id, const uint8_t *payload, size_t payload_len,
                           uint8_t *out_buf, size_t max_len, size_t *out_len)
{
    /* MQTT-SN short header: Len(1), Type(1), Flags(1), TopicId(2), MsgId(2), Data(N) */
    size_t total_len = 7 + payload_len;
    if (max_len < total_len || total_len > 255) {
        return -1;
    }

    out_buf[0] = (uint8_t)total_len;
    out_buf[1] = MQTTSN_TYPE_PUBLISH;
    out_buf[2] = 0x00; /* QoS 0, normal topic ID */
    out_buf[3] = (uint8_t)(topic_id >> 8);
    out_buf[4] = (uint8_t)topic_id;
    out_buf[5] = (uint8_t)(msg_id >> 8);
    out_buf[6] = (uint8_t)msg_id;

    if (payload_len > 0 && payload != NULL) {
        memcpy(&out_buf[7], payload, payload_len);
    }

    *out_len = total_len;
    return 0;
}

int mqtt_sn_decode_header(const uint8_t *buf, size_t len, uint8_t *msg_type, size_t *header_len)
{
    if (!buf || len < 2) {
        return -1;
    }

    uint8_t length = buf[0];
    if (length == 0x01) {
        /* Extended 3-byte length header */
        if (len < 4) return -1;
        *msg_type = buf[3];
        *header_len = 4;
    } else {
        *msg_type = buf[1];
        *header_len = 2;
    }

    return 0;
}
