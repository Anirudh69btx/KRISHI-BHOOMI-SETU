#ifndef FLIP_SENSOR_RAIN_GAUGE_H_
#define FLIP_SENSOR_RAIN_GAUGE_H_

#include <zephyr/kernel.h>

#ifdef __cplusplus
extern "C" {
#endif

int rain_gauge_init(void);
float rain_gauge_get_and_reset(void);
float rain_gauge_get_rate_mm_per_hr(void);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_SENSOR_RAIN_GAUGE_H_ */
