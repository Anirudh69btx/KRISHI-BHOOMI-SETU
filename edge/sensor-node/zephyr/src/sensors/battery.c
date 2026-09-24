#include "battery.h"
#include <zephyr/device.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(sensor_battery, LOG_LEVEL_INF);

#define ADC_NODE DT_NODELABEL(adc0)

#if DT_NODE_HAS_STATUS(ADC_NODE, okay)
static const struct device *const adc_dev = DEVICE_DT_GET(ADC_NODE);
#else
static const struct device *const adc_dev = NULL;
#endif

#define ADC_CHANNEL_BATT 3
#define ADC_RESOLUTION   12
/* 100k / 100k voltage divider ratio = 2.0 */
#define DIVIDER_RATIO    2.0f

/* LiFePO4 OCV Lookup Table: (mV, SoC %) */
struct ocv_entry {
    uint16_t mv;
    uint8_t soc;
};

static const struct ocv_entry ocv_table[] = {
    {3100, 0},
    {3200, 0},
    {3300, 20},
    {3350, 50},
    {3400, 80},
    {3450, 100},
    {3650, 100},
};
#define OCV_TABLE_LEN (sizeof(ocv_table) / sizeof(ocv_table[0]))

/* 10-point moving average filter */
#define BATT_WINDOW_SIZE 10
static uint16_t batt_history[BATT_WINDOW_SIZE] = {3300, 3300, 3300, 3300, 3300, 3300, 3300, 3300, 3300, 3300};
static size_t batt_idx = 0;
static uint16_t prev_filtered_mv = 3300;

static uint16_t apply_batt_filter(uint16_t raw_mv)
{
    batt_history[batt_idx] = raw_mv;
    batt_idx = (batt_idx + 1) % BATT_WINDOW_SIZE;

    uint32_t sum = 0;
    for (size_t i = 0; i < BATT_WINDOW_SIZE; i++) {
        sum += batt_history[i];
    }
    return (uint16_t)(sum / BATT_WINDOW_SIZE);
}

int battery_init(void)
{
    if (!adc_dev || !device_is_ready(adc_dev)) {
        LOG_WRN("ADC device for battery not ready (simulation mode active)");
        return 0;
    }
    LOG_INF("LiFePO4 battery monitor initialized on ADC Ch %d", ADC_CHANNEL_BATT);
    return 0;
}

uint16_t battery_read_mv(void)
{
    uint16_t current_raw = 3320;

    if (adc_dev && device_is_ready(adc_dev)) {
        int16_t sample_buffer = 0;
        struct adc_channel_cfg channel_cfg = {
            .gain = ADC_GAIN_1,
            .reference = ADC_REF_INTERNAL,
            .acquisition_time = ADC_ACQ_TIME_DEFAULT,
            .channel_id = ADC_CHANNEL_BATT,
        };
        adc_channel_setup(adc_dev, &channel_cfg);

        struct adc_sequence seq = {
            .channels = BIT(ADC_CHANNEL_BATT),
            .buffer = &sample_buffer,
            .buffer_size = sizeof(sample_buffer),
            .resolution = ADC_RESOLUTION,
        };

        int ret = adc_read(adc_dev, &seq);
        if (ret == 0) {
            int32_t val_mv = sample_buffer;
            adc_raw_to_millivolts(adc_ref_internal(adc_dev), ADC_GAIN_1, ADC_RESOLUTION, &val_mv);
            current_raw = (uint16_t)((float)val_mv * DIVIDER_RATIO);
        }
    }

    uint16_t filtered = apply_batt_filter(current_raw);
    prev_filtered_mv = filtered;
    return filtered;
}

uint8_t battery_soc_percent(uint16_t mv)
{
    if (mv <= ocv_table[0].mv) return 0;
    if (mv >= ocv_table[OCV_TABLE_LEN - 1].mv) return 100;

    /* Piecewise linear interpolation over OCV lookup table */
    for (size_t i = 0; i < OCV_TABLE_LEN - 1; i++) {
        if (mv >= ocv_table[i].mv && mv <= ocv_table[i + 1].mv) {
            uint16_t v_span = ocv_table[i + 1].mv - ocv_table[i].mv;
            uint8_t soc_span = ocv_table[i + 1].soc - ocv_table[i].soc;
            uint16_t v_diff = mv - ocv_table[i].mv;
            return ocv_table[i].soc + (uint8_t)(((uint32_t)v_diff * soc_span) / v_span);
        }
    }
    return 50;
}

bool battery_is_low_alert(void)
{
    return (prev_filtered_mv < 3100);
}

bool battery_is_charging(void)
{
    // Voltage above 3.6V indicates active MPPT absorption charge
    return (prev_filtered_mv > 3550);
}
