#ifndef FLIP_POWER_SOLAR_CHARGER_H_
#define FLIP_POWER_SOLAR_CHARGER_H_

#include <zephyr/kernel.h>
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum solar_charge_state {
    SOLAR_CHARGING_OFF   = 0,
    SOLAR_CHARGING_BULK  = 1,
    SOLAR_CHARGING_FLOAT = 2,
    SOLAR_FAULT          = 3,
};

int solar_charger_init(void);
enum solar_charge_state solar_charger_get_status(uint16_t *solar_panel_mv, uint16_t *charge_current_ma);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_POWER_SOLAR_CHARGER_H_ */
