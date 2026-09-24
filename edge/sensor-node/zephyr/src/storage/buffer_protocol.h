#ifndef FLIP_STORAGE_BUFFER_PROTOCOL_H_
#define FLIP_STORAGE_BUFFER_PROTOCOL_H_

#include <zephyr/kernel.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

int buffer_protocol_flush_batch(size_t max_packets);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_STORAGE_BUFFER_PROTOCOL_H_ */
