#include "leaf_wetness.h"
#include <zephyr/device.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(sensor_leaf_wetness, LOG_LEVEL_INF);

#define ADC_NODE DT_NODELABEL(adc0)

#if DT_NODE_HAS_STATUS(ADC_NODE, okay)
static const struct device *const adc_dev = DEVICE_DT_GET(ADC_NODE);
#else
static const struct device *const adc_dev = NULL;
#endif

#define ADC_CHANNEL_LW 1
#define ADC_RESOLUTION 12

/* Calibration reference voltages (mV) */
#define CAL_DRY_MV 2800  // High resistance when completely dry
#define CAL_WET_MV 450   // Low resistance when fully saturated with water/dew

/* Hysteresis thresholds */
#define THRESHOLD_WET_ON  0.50f
#define THRESHOLD_WET_OFF 0.30f
#define DEBOUNCE_COUNT    5

static bool current_wet_state = false;
static uint8_t debounce_counter = 0;
static int64_t wet_start_time_ms = 0;
static uint32_t continuous_wet_minutes = 0;

int leaf_wetness_init(void)
{
    if (!adc_dev || !device_is_ready(adc_dev)) {
        LOG_WRN("ADC device for Leaf Wetness not ready (simulation mode)");
        return 0;
    }
    LOG_INF("Dielectric Leaf Wetness sensor initialized on ADC Ch %d", ADC_CHANNEL_LW);
    return 0;
}

int leaf_wetness_read(float *wetness_index)
{
    if (!wetness_index) {
        return -EINVAL;
    }

    int32_t val_mv = CAL_DRY_MV;

    if (adc_dev && device_is_ready(adc_dev)) {
        int16_t sample_buffer = 0;
        struct adc_channel_cfg channel_cfg = {
            .gain = ADC_GAIN_1,
            .reference = ADC_REF_INTERNAL,
            .acquisition_time = ADC_ACQ_TIME_DEFAULT,
            .channel_id = ADC_CHANNEL_LW,
            .differential = 0, // Single-ended on GPIO1
        };
        adc_channel_setup(adc_dev, &channel_cfg);

        struct adc_sequence seq = {
            .channels = BIT(ADC_CHANNEL_LW),
            .buffer = &sample_buffer,
            .buffer_size = sizeof(sample_buffer),
            .resolution = ADC_RESOLUTION,
        };

        int ret = adc_read(adc_dev, &seq);
        if (ret == 0) {
            val_mv = sample_buffer;
            adc_raw_to_millivolts(adc_ref_internal(adc_dev), ADC_GAIN_1, ADC_RESOLUTION, &val_mv);
        }
    } else {
        val_mv = 1600; // Simulated intermediate reading
    }

    /* Normalization: 0.0 (dry) to 1.0 (saturated) via calibration endpoints */
    float norm = ((float)CAL_DRY_MV - (float)val_mv) / ((float)CAL_DRY_MV - (float)CAL_WET_MV);
    if (norm < 0.0f) norm = 0.0f;
    if (norm > 1.0f) norm = 1.0f;
    *wetness_index = norm;

    /* Threshold detection with 5-count hysteresis debouncing */
    if (!current_wet_state) {
        if (norm > THRESHOLD_WET_ON) {
            debounce_counter++;
            if (debounce_counter >= DEBOUNCE_COUNT) {
                current_wet_state = true;
                wet_start_time_ms = k_uptime_get();
                debounce_counter = 0;
                LOG_INF("🌿 Leaf transition to WET detected");
            }
        } else {
            debounce_counter = 0;
        }
    } else {
        if (norm < THRESHOLD_WET_OFF) {
            debounce_counter++;
            if (debounce_counter >= DEBOUNCE_COUNT) {
                current_wet_state = false;
                debounce_counter = 0;
                LOG_INF("🍂 Leaf transition to DRY detected");
            }
        } else {
            debounce_counter = 0;
        }
    }

    /* Duration counter: update minutes continuous wet for fungal disease modeling */
    if (current_wet_state && wet_start_time_ms > 0) {
        continuous_wet_minutes = (uint32_t)((k_uptime_get() - wet_start_time_ms) / 60000);
    } else {
        continuous_wet_minutes = 0;
    }

    return 0;
}

bool leaf_wetness_is_wet(void)
{
    return current_wet_state;
}

uint32_t leaf_wetness_get_duration_minutes(void)
{
    return continuous_wet_minutes;
}
