#ifndef FLIP_SENSOR_BATTERY_H_
#define FLIP_SENSOR_BATTERY_H_

#include <zephyr/kernel.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

int battery_init(void);
uint16_t battery_read_mv(void);
uint8_t battery_soc_percent(uint16_t mv);
bool battery_is_low_alert(void);
bool battery_is_charging(void);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_SENSOR_BATTERY_H_ */
