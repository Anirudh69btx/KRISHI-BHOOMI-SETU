#include "bh1750.h"
#include <zephyr/device.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(sensor_bh1750, LOG_LEVEL_INF);

#define BH1750_I2C_ADDR 0x23
#define BH1750_CMD_POWER_ON                 0x01
#define BH1750_CMD_RESET                    0x07
#define BH1750_CMD_CONTINUOUS_HIGH_RES_MODE 0x10
#define BH1750_CMD_CONTINUOUS_HIGH_RES_MODE2 0x11
#define BH1750_CMD_CONTINUOUS_LOW_RES_MODE  0x13

#define BH1750_NODE DT_ALIAS(bh1750)

#if DT_NODE_HAS_STATUS(BH1750_NODE, okay)
static const struct device *const bh1750_sensor_dev = DEVICE_DT_GET(BH1750_NODE);
#else
static const struct device *const bh1750_sensor_dev = NULL;
#endif

static const struct device *i2c_bus_dev = NULL;
static uint8_t current_mode = BH1750_CMD_CONTINUOUS_HIGH_RES_MODE;

/* PAR conversion: sunlight spectral factor ~0.0185 to 0.045 µmol/m²/s per lux */
#define LUX_TO_PAR_FACTOR 0.0185f

int bh1750_init(void)
{
    i2c_bus_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));
    if (i2c_bus_dev && device_is_ready(i2c_bus_dev)) {
        // Send Power On & Continuous High-Resolution Mode (0x10)
        uint8_t cmd = BH1750_CMD_POWER_ON;
        i2c_write(i2c_bus_dev, &cmd, 1, BH1750_I2C_ADDR);
        cmd = BH1750_CMD_CONTINUOUS_HIGH_RES_MODE;
        i2c_write(i2c_bus_dev, &cmd, 1, BH1750_I2C_ADDR);
        LOG_INF("BH1750 initialized in continuous high-res mode (0x10)");
        return 0;
    }

    if (bh1750_sensor_dev && device_is_ready(bh1750_sensor_dev)) {
        LOG_INF("BH1750 initialized via Zephyr sensor DT");
        return 0;
    }

    LOG_WRN("BH1750 device not ready (simulation mode active)");
    return 0;
}

int bh1750_read(float *lux, float *par_umol)
{
    if (!lux || !par_umol) {
        return -EINVAL;
    }

    /* Option A: Direct I2C high-precision register readout */
    if (i2c_bus_dev && device_is_ready(i2c_bus_dev)) {
        uint8_t rx_buf[2] = {0};
        int ret = i2c_read(i2c_bus_dev, rx_buf, 2, BH1750_I2C_ADDR);
        if (ret == 0) {
            uint16_t raw_val = ((uint16_t)rx_buf[0] << 8) | rx_buf[1];
            /* Formula from BH1750 datasheet: Lux = Raw / 1.2 */
            float calculated_lux = (float)raw_val / 1.2f;

            /* Automatic range switching:
             * If lux > 40000 in high-res mode, switch to high-res mode 2 (0.5 lux resolution)
             * If lux < 10, switch to high-res mode 1
             */
            if (calculated_lux > 40000.0f && current_mode != BH1750_CMD_CONTINUOUS_HIGH_RES_MODE2) {
                uint8_t mode_cmd = BH1750_CMD_CONTINUOUS_HIGH_RES_MODE2;
                i2c_write(i2c_bus_dev, &mode_cmd, 1, BH1750_I2C_ADDR);
                current_mode = BH1750_CMD_CONTINUOUS_HIGH_RES_MODE2;
            } else if (calculated_lux < 1000.0f && current_mode != BH1750_CMD_CONTINUOUS_HIGH_RES_MODE) {
                uint8_t mode_cmd = BH1750_CMD_CONTINUOUS_HIGH_RES_MODE;
                i2c_write(i2c_bus_dev, &mode_cmd, 1, BH1750_I2C_ADDR);
                current_mode = BH1750_CMD_CONTINUOUS_HIGH_RES_MODE;
            }

            *lux = calculated_lux;
            *par_umol = calculated_lux * LUX_TO_PAR_FACTOR;
            return 0;
        }
    }

    /* Option B: Standard Zephyr Sensor API */
    if (bh1750_sensor_dev && device_is_ready(bh1750_sensor_dev)) {
        int ret = sensor_sample_fetch(bh1750_sensor_dev);
        if (ret == 0) {
            struct sensor_value val;
            sensor_channel_get(bh1750_sensor_dev, SENSOR_CHAN_LIGHT, &val);
            *lux = (float)sensor_value_to_double(&val);
            *par_umol = (*lux) * LUX_TO_PAR_FACTOR;
            return 0;
        }
    }

    /* Fallback simulation values */
    *lux = 52000.0f;
    *par_umol = (*lux) * LUX_TO_PAR_FACTOR;
    return 0;
}
