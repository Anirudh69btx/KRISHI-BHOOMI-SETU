#ifndef FLIP_SENSOR_LEAF_WETNESS_H_
#define FLIP_SENSOR_LEAF_WETNESS_H_

#include <zephyr/kernel.h>
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

int leaf_wetness_init(void);
int leaf_wetness_read(float *wetness_index);
bool leaf_wetness_is_wet(void);
uint32_t leaf_wetness_get_duration_minutes(void);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_SENSOR_LEAF_WETNESS_H_ */
