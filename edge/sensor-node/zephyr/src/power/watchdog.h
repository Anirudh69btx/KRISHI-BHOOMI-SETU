#ifndef FLIP_POWER_WATCHDOG_H_
#define FLIP_POWER_WATCHDOG_H_

#include <zephyr/kernel.h>

#ifdef __cplusplus
extern "C" {
#endif

int watchdog_init(uint32_t timeout_ms);
void watchdog_feed(void);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_POWER_WATCHDOG_H_ */
