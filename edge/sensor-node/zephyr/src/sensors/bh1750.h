#ifndef FLIP_SENSOR_BH1750_H_
#define FLIP_SENSOR_BH1750_H_

#include <zephyr/kernel.h>

#ifdef __cplusplus
extern "C" {
#endif

int bh1750_init(void);
int bh1750_read(float *lux, float *par_umol);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_SENSOR_BH1750_H_ */
