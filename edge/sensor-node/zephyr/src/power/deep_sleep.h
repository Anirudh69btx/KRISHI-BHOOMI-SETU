#ifndef FLIP_POWER_DEEP_SLEEP_H_
#define FLIP_POWER_DEEP_SLEEP_H_

#include <zephyr/kernel.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum node_pm_state {
    PM_STATE_ACTIVE      = 0,
    PM_STATE_SENSOR_READ = 1,
    PM_STATE_TX          = 2,
    PM_STATE_DEEP_SLEEP  = 3,
};

int deep_sleep_init(void);
void deep_sleep_set_state(enum node_pm_state state);
enum node_pm_state deep_sleep_get_state(void);
void deep_sleep_enter_minutes(uint32_t minutes);
void deep_sleep_enter_seconds(uint32_t seconds);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_POWER_DEEP_SLEEP_H_ */
