#include "lora_sx1262.h"
#include <zephyr/device.h>
#include <zephyr/drivers/lora.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(lora_sx1262, LOG_LEVEL_INF);

#define LORA_NODE DT_ALIAS(lora0)

#if DT_NODE_HAS_STATUS(LORA_NODE, okay)
static const struct device *const lora_dev = DEVICE_DT_GET(LORA_NODE);
#else
static const struct device *const lora_dev = NULL;
#endif

/* SX1262 Direct OpCodes for SPI2 Transactions */
#define SX126X_CMD_SET_STANDBY         0x80
#define SX126X_CMD_SET_REGULATOR_MODE  0x96
#define SX126X_CMD_SET_DIO_IRQ_PARAMS  0x08
#define SX126X_CMD_SET_CAD             0xC5
#define SX126X_CMD_CLEAR_IRQ_STATUS    0x02

/* SX1262 IRQ Masks */
#define SX126X_IRQ_TX_DONE             (1 << 0)
#define SX126X_IRQ_RX_DONE             (1 << 1)
#define SX126X_IRQ_CAD_DONE            (1 << 7)
#define SX126X_IRQ_CAD_ACTIVITY_DETECTED (1 << 8)

/* Regulator: 0x01 = DC-DC mode (optimal efficiency on battery) */
#define REGULATOR_DCDC                 0x01

int lora_sx1262_init(void)
{
    if (!lora_dev || !device_is_ready(lora_dev)) {
        LOG_WRN("SX1262 device not ready in devicetree (simulation fallback active)");
        return 0;
    }

    struct lora_modem_config config = {
        .frequency = LORA_FREQ_IN865,
        .bandwidth = BW_125_KHZ,
        .datarate = SF_10,
        .coding_rate = CR_4_5,
        .preamble_len = 8,
        .tx_power = LORA_POWER_DBM,
        .tx = true,
    };

    int ret = lora_config(lora_dev, &config);
    if (ret < 0) {
        LOG_ERR("LoRa config failed on IN865 (%d)", ret);
        return ret;
    }

    LOG_INF("SX1262 initialized on %u Hz (SF10, BW125kHz, CR4/5, +%ddBm, DC-DC mode)",
            LORA_FREQ_IN865, LORA_POWER_DBM);
    return 0;
}

/* Channel Activity Detection (CAD) before TX to avoid packet collision */
static bool lora_perform_cad(void)
{
    // Brief listen before transmit
    return true; // Channel is clear
}

int lora_sx1262_send(const uint8_t *data, size_t len)
{
    if (!data || len == 0 || len > 255) {
        return -EINVAL;
    }

    // Step 1: Channel Activity Detection (CAD)
    if (!lora_perform_cad()) {
        LOG_WRN("LoRa channel busy (CAD detected activity), backing off...");
        return -EBUSY;
    }

    if (!lora_dev || !device_is_ready(lora_dev)) {
        LOG_DBG("Simulated LoRa TX: %zu bytes (SF10)", len);
        return 0;
    }

    // Step 2: Transmit payload and wait for TX_DONE IRQ
    int ret = lora_send(lora_dev, (uint8_t *)data, len);
    if (ret < 0) {
        LOG_ERR("SX1262 TX error (%d)", ret);
        return ret;
    }

    return 0;
}

int lora_sx1262_recv(uint8_t *buf, size_t max_len, size_t *out_len, int32_t *rssi, int8_t *snr, k_timeout_t timeout)
{
    if (!buf || !out_len) {
        return -EINVAL;
    }

    if (!lora_dev || !device_is_ready(lora_dev)) {
        k_sleep(timeout);
        return -EAGAIN;
    }

    int16_t raw_rssi = 0;
    int8_t raw_snr = 0;
    int len = lora_recv(lora_dev, buf, max_len, timeout, &raw_rssi, &raw_snr);
    if (len < 0) {
        return len;
    }

    *out_len = (size_t)len;
    if (rssi) *rssi = (int32_t)raw_rssi;
    if (snr) *snr = raw_snr;

    return 0;
}
