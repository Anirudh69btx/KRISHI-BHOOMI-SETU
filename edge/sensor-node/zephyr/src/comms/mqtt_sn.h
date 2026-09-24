#ifndef FLIP_COMMS_MQTT_SN_H_
#define FLIP_COMMS_MQTT_SN_H_

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MQTTSN_TYPE_CONNECT    0x04
#define MQTTSN_TYPE_CONNACK    0x05
#define MQTTSN_TYPE_REGISTER   0x0A
#define MQTTSN_TYPE_REGACK     0x0B
#define MQTTSN_TYPE_PUBLISH    0x0C
#define MQTTSN_TYPE_PUBACK     0x0D
#define MQTTSN_TYPE_DISCONNECT 0x18

int mqtt_sn_encode_publish(uint16_t topic_id, uint16_t msg_id, const uint8_t *payload, size_t payload_len,
                           uint8_t *out_buf, size_t max_len, size_t *out_len);

int mqtt_sn_decode_header(const uint8_t *buf, size_t len, uint8_t *msg_type, size_t *header_len);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_COMMS_MQTT_SN_H_ */
