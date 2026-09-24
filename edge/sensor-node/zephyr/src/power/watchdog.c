#include "watchdog.h"
#include <zephyr/device.h>
#include <zephyr/drivers/watchdog.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(power_wdt, LOG_LEVEL_INF);

#define WDT_NODE DT_ALIAS(wdt)

#if DT_NODE_HAS_STATUS(WDT_NODE, okay)
static const struct device *const wdt_dev = DEVICE_DT_GET(WDT_NODE);
#else
static const struct device *const wdt_dev = NULL;
#endif

static int wdt_channel_id = -1;

int watchdog_init(uint32_t timeout_ms)
{
    if (!wdt_dev || !device_is_ready(wdt_dev)) {
        LOG_WRN("Hardware Watchdog device not ready");
        return -ENODEV;
    }

    struct wdt_timeout_cfg wdt_config = {
        .window = {
            .min = 0,
            .max = timeout_ms,
        },
        .callback = NULL,
        .flags = WDT_FLAG_RESET_SOC,
    };

    wdt_channel_id = wdt_install_timeout(wdt_dev, &wdt_config);
    if (wdt_channel_id < 0) {
        LOG_ERR("Watchdog install timeout failed (%d)", wdt_channel_id);
        return wdt_channel_id;
    }

    int ret = wdt_setup(wdt_dev, WDT_OPT_PAUSE_HALTED_BY_DBG);
    if (ret < 0) {
        LOG_ERR("Watchdog setup failed (%d)", ret);
        return ret;
    }

    LOG_INF("Watchdog configured with %u ms window (channel=%d)", timeout_ms, wdt_channel_id);
    return 0;
}

void watchdog_feed(void)
{
    if (wdt_dev && device_is_ready(wdt_dev) && wdt_channel_id >= 0) {
        wdt_feed(wdt_dev, wdt_channel_id);
    }
}
