#include "rain_gauge.h"
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(sensor_rain_gauge, LOG_LEVEL_INF);

#define RAIN_PIN_NODE DT_NODELABEL(rain_gauge_pin)

#if DT_NODE_EXISTS(RAIN_PIN_NODE)
static const struct gpio_dt_spec rain_gpio = GPIO_DT_SPEC_GET(RAIN_PIN_NODE, gpios);
#else
static const struct gpio_dt_spec rain_gpio = {0};
#endif

#define MM_PER_TIP 0.2f
#define DEBOUNCE_LOCKOUT_MS 5 // 5ms hardware reed switch lockout window

static struct gpio_callback rain_cb_data;
static volatile uint32_t total_tip_count = 0;
static volatile int64_t last_tip_timestamp_ms = 0;

/* 1-minute sliding window for rainfall rate (12 x 5-second buckets) */
#define WINDOW_BUCKETS 12
static uint16_t rate_buckets[WINDOW_BUCKETS] = {0};
static size_t current_bucket = 0;
static int64_t last_bucket_advance_ms = 0;

static void rain_gpio_isr(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
    int64_t now = k_uptime_get();
    if ((now - last_tip_timestamp_ms) >= DEBOUNCE_LOCKOUT_MS) {
        total_tip_count++;
        rate_buckets[current_bucket]++;
        last_tip_timestamp_ms = now;
    }
}

int rain_gauge_init(void)
{
    if (!rain_gpio.port || !device_is_ready(rain_gpio.port)) {
        LOG_WRN("Rain gauge GPIO port not ready (simulation mode)");
        return 0;
    }

    int ret = gpio_pin_configure_dt(&rain_gpio, GPIO_INPUT | GPIO_PULL_UP);
    if (ret < 0) {
        LOG_ERR("Failed to configure rain gauge pin (%d)", ret);
        return ret;
    }

    // Trigger on rising edge (reed switch release / pulse transition)
    ret = gpio_pin_interrupt_configure_dt(&rain_gpio, GPIO_INT_EDGE_RISING);
    if (ret < 0) {
        LOG_ERR("Failed to configure rain interrupt (%d)", ret);
        return ret;
    }

    gpio_init_callback(&rain_cb_data, rain_gpio_isr, BIT(rain_gpio.pin));
    gpio_add_callback(rain_gpio.port, &rain_cb_data);

    last_bucket_advance_ms = k_uptime_get();
    LOG_INF("Tipping bucket rain gauge initialized on GPIO pin %d (0.2mm/tip, 5ms debounce)", rain_gpio.pin);
    return 0;
}

float rain_gauge_get_and_reset(void)
{
    uint32_t count = total_tip_count;
    total_tip_count = 0;
    return (float)count * MM_PER_TIP;
}

float rain_gauge_get_rate_mm_per_hr(void)
{
    int64_t now = k_uptime_get();
    if ((now - last_bucket_advance_ms) >= 5000) { // 5s per bucket
        size_t steps = (size_t)((now - last_bucket_advance_ms) / 5000);
        for (size_t i = 0; i < steps && i < WINDOW_BUCKETS; i++) {
            current_bucket = (current_bucket + 1) % WINDOW_BUCKETS;
            rate_buckets[current_bucket] = 0;
        }
        last_bucket_advance_ms = now;
    }

    uint32_t window_tips = 0;
    for (size_t i = 0; i < WINDOW_BUCKETS; i++) {
        window_tips += rate_buckets[i];
    }

    /* Total mm in 1 minute * 60 = mm/hr */
    float mm_in_minute = (float)window_tips * MM_PER_TIP;
    float rate_mm_per_hr = mm_in_minute * 60.0f;
    return rate_mm_per_hr;
}
