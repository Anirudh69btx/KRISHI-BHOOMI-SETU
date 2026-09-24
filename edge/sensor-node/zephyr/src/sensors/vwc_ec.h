#ifndef FLIP_SENSOR_VWC_EC_H_
#define FLIP_SENSOR_VWC_EC_H_

#include <zephyr/kernel.h>

#ifdef __cplusplus
extern "C" {
#endif

int vwc_ec_init(void);
int vwc_ec_read(float *vwc_percent, float *ec_ds_m, float *soil_temp_c);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_SENSOR_VWC_EC_H_ */
