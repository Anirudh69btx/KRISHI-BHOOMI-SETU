#ifndef FLIP_COMMS_LORA_SX1262_H_
#define FLIP_COMMS_LORA_SX1262_H_

#include <zephyr/kernel.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define LORA_FREQ_IN865  865000000  /* 865 MHz Indian ISM Band */
#define LORA_BW_DEFAULT  125000     /* 125 kHz Bandwidth */
#define LORA_SF_DEFAULT  10         /* Spreading Factor 10 */
#define LORA_CR_DEFAULT  5          /* Coding Rate 4/5 */
#define LORA_POWER_DBM   14         /* 14 dBm transmit power */

int lora_sx1262_init(void);
int lora_sx1262_send(const uint8_t *data, size_t len);
int lora_sx1262_recv(uint8_t *buf, size_t max_len, size_t *out_len, int32_t *rssi, int8_t *snr, k_timeout_t timeout);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_COMMS_LORA_SX1262_H_ */
