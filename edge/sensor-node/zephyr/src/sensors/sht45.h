#ifndef FLIP_SENSOR_SHT45_H_
#define FLIP_SENSOR_SHT45_H_

#include <zephyr/kernel.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

int sht45_init(void);
int sht45_read(float *temperature_c, float *relative_humidity);
int sht45_set_heater(bool enable);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_SENSOR_SHT45_H_ */
