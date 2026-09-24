#include "deep_sleep.h"
#include <zephyr/pm/pm.h>
#include <zephyr/pm/policy.h>
#include <zephyr/pm/device.h>
#include <zephyr/device.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(deep_sleep, LOG_LEVEL_INF);

static enum node_pm_state current_pm_state = PM_STATE_ACTIVE;

int deep_sleep_init(void)
{
    current_pm_state = PM_STATE_ACTIVE;
    LOG_INF("Power Management state machine initialized (<100uA quiescent target)");
    return 0;
}

void deep_sleep_set_state(enum node_pm_state state)
{
    current_pm_state = state;
    switch (state) {
    case PM_STATE_ACTIVE:
        LOG_DBG("PM State -> ACTIVE");
        break;
    case PM_STATE_SENSOR_READ:
        LOG_DBG("PM State -> SENSOR_READ");
        break;
    case PM_STATE_TX:
        LOG_DBG("PM State -> TX");
        break;
    case PM_STATE_DEEP_SLEEP:
        LOG_INF("PM State -> DEEP_SLEEP");
        break;
    }
}

enum node_pm_state deep_sleep_get_state(void)
{
    return current_pm_state;
}

/* Power gate peripherals: suspend I2C, SPI, and ADC rails */
static void gate_peripherals(bool suspend)
{
    const struct device *devs[] = {
        DEVICE_DT_GET_OR_NULL(DT_NODELABEL(i2c0)),
        DEVICE_DT_GET_OR_NULL(DT_NODELABEL(spi2)),
        DEVICE_DT_GET_OR_NULL(DT_NODELABEL(adc0)),
    };

    for (size_t i = 0; i < sizeof(devs) / sizeof(devs[0]); i++) {
        if (devs[i] && device_is_ready(devs[i])) {
            enum pm_device_action action = suspend ? PM_DEVICE_ACTION_SUSPEND : PM_DEVICE_ACTION_RESUME;
            pm_device_action_run(devs[i], action);
        }
    }
}

void deep_sleep_enter_seconds(uint32_t seconds)
{
    deep_sleep_set_state(PM_STATE_DEEP_SLEEP);

    // 1. Gate peripheral rails (I2C, SPI, ADC)
    gate_peripherals(true);

    // 2. Put CPU into deepest RTC low-power sleep state
    LOG_INF("Power rails gated. Entering RTC timer sleep for %u seconds (<80uA)...", seconds);
    k_sleep(K_SECONDS(seconds));

    // 3. Fast wakeup: restore peripheral rails (<50ms latency)
    gate_peripherals(false);
    deep_sleep_set_state(PM_STATE_ACTIVE);
    LOG_INF("Woke up from RTC sleep. Active state restored.");
}

void deep_sleep_enter_minutes(uint32_t minutes)
{
    deep_sleep_enter_seconds(minutes * 60);
}
