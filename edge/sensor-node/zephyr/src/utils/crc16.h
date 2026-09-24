#ifndef FLIP_UTILS_CRC16_H_
#define FLIP_UTILS_CRC16_H_

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

uint16_t crc16_ccitt(const uint8_t *data, size_t len);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_UTILS_CRC16_H_ */
