#include "solar_charger.h"
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(solar_charger, LOG_LEVEL_INF);

int solar_charger_init(void)
{
    LOG_INF("CN3791 MPPT Solar Charger monitor initialized");
    return 0;
}

enum solar_charge_state solar_charger_get_status(uint16_t *solar_panel_mv, uint16_t *charge_current_ma)
{
    /* Realistic solar harvest simulation for 6V-10W panel in day */
    if (solar_panel_mv) *solar_panel_mv = 5850; /* 5.85V under load */
    if (charge_current_ma) *charge_current_ma = 850; /* 850mA bulk charge */

    return SOLAR_CHARGING_BULK;
}
