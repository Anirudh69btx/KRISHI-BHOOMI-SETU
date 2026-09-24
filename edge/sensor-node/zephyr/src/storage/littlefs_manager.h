#ifndef FLIP_STORAGE_LITTLEFS_MANAGER_H_
#define FLIP_STORAGE_LITTLEFS_MANAGER_H_

#include <zephyr/kernel.h>
#include "../utils/cbor_codec.h"

#ifdef __cplusplus
extern "C" {
#endif

int littlefs_init(void);
int littlefs_write_packet(const struct sensor_packet *pkt);
int littlefs_read_next_buffered(struct sensor_packet *pkt, uint16_t *out_seq_id);
int littlefs_delete_packet(uint16_t seq_id);
size_t littlefs_get_buffered_count(void);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_STORAGE_LITTLEFS_MANAGER_H_ */
