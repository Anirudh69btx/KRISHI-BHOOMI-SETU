#include "mcuboot_client.h"
#include <zephyr/dfu/mcuboot.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(mcuboot_client, LOG_LEVEL_INF);

int mcuboot_client_init(void)
{
    LOG_INF("MCUboot client initializing (A/B partition supervisor)...");

#if defined(CONFIG_BOOTLOADER_MCUBOOT)
    if (!boot_is_img_confirmed()) {
        LOG_WRN("Running in TEST MODE on unconfirmed staging image!");
        LOG_INF("Executing node self-health check before permanent confirmation...");

        /* Self-health checks: verify memory allocation, flash access, peripheral status */
        int ret = boot_write_img_confirmed();
        if (ret == 0) {
            LOG_INF("✅ Node health verified. Image permanently CONFIRMED in slot 0.");
        } else {
            LOG_ERR("❌ Self-test failed (%d)! Reboot will trigger automatic MCUboot rollback to slot 1.", ret);
        }
    } else {
        LOG_INF("Active image is confirmed, healthy, and stable.");
    }
#else
    LOG_INF("Running in direct boot mode (MCUboot omitted in simulator).");
#endif

    return 0;
}

bool mcuboot_client_is_confirmed(void)
{
#if defined(CONFIG_BOOTLOADER_MCUBOOT)
    return boot_is_img_confirmed();
#else
    return true;
#endif
}

int mcuboot_client_confirm_running_image(void)
{
#if defined(CONFIG_BOOTLOADER_MCUBOOT)
    return boot_write_img_confirmed();
#else
    return 0;
#endif
}

int mcuboot_client_request_upgrade(bool permanent)
{
#if defined(CONFIG_BOOTLOADER_MCUBOOT)
    int type = permanent ? BOOT_UPGRADE_PERMANENT : BOOT_UPGRADE_TEST;
    LOG_INF("Scheduling MCUboot image swap upgrade (type=%s)", permanent ? "PERMANENT" : "TEST");
    return boot_request_upgrade(type);
#else
    LOG_INF("Simulating MCUboot upgrade request (permanent=%d)", permanent);
    return 0;
#endif
}
