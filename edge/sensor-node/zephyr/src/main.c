/*
 * FLIP (Farm Lifecycle Intelligence Platform)
 * Agricultural IoT Sensor Node Firmware — Zephyr RTOS
 * Target: ESP32-C3 RISC-V SoC + SX1262 LoRa + Sensors
 */

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/device.h>
#include <zephyr/sys/printk.h>

/* Subsystem drivers */
#include "sensors/sht45.h"
#include "sensors/vwc_ec.h"
#include "sensors/leaf_wetness.h"
#include "sensors/rain_gauge.h"
#include "sensors/bh1750.h"
#include "sensors/battery.h"

#include "comms/lora_sx1262.h"
#include "comms/protocol.h"
#include "comms/mqtt_sn.h"

#include "storage/littlefs_manager.h"
#include "storage/buffer_protocol.h"

#include "ota/mcuboot_client.h"
#include "ota/sigstore_verify.h"

#include "power/deep_sleep.h"
#include "power/solar_charger.h"
#include "power/watchdog.h"

#include "utils/cbor_codec.h"
#include "utils/crc16.h"

LOG_MODULE_REGISTER(sensor_node, LOG_LEVEL_INF);

#define FIRMWARE_VERSION "1.0.0"
#define SLEEP_INTERVAL_MIN 15
#define MAX_TX_RETRIES 3
#define WDT_TIMEOUT_MS 30000

static struct sensor_packet current_pkt;
static uint16_t sequence_id = 0;
static bool gateway_online = false;

static void get_device_mac(uint8_t mac[8])
{
    /* Deterministic 8-byte device identifier */
    mac[0] = 0xF0;
    mac[1] = 0xDE;
    mac[2] = 0xF1;
    mac[3] = 0x10;
    mac[4] = 0x00;
    mac[5] = 0x00;
    mac[6] = 0x01;
    mac[7] = 0x01;
}

static void process_gateway_response(const uint8_t *rx_buf, size_t rx_len)
{
    uint8_t msg_type = 0;
    uint16_t seq = 0;
    const uint8_t *payload = NULL;
    uint8_t payload_len = 0;

    uint8_t dev_id[8] = {0};
    int ret = flip_protocol_parse(rx_buf, rx_len, &msg_type, &seq, dev_id, &payload, &payload_len);
    if (ret != 0) {
        LOG_WRN("Received unparseable LoRa frame (%d)", ret);
        return;
    }

    if (msg_type == FLIP_MSG_ACK) {
        gateway_online = true;
        LOG_INF("Gateway ACK confirmed for seq=%u", seq);
    } else if (msg_type == FLIP_MSG_OTA_TRIGGER) {
        LOG_INF("Gateway initiated OTA upgrade trigger!");
        mcuboot_client_request_upgrade(false);
    }
}

int main(void)
{
    LOG_INF("=================================================");
    LOG_INF("  FLIP Sensor Node v%s (Zephyr RTOS)", FIRMWARE_VERSION);
    LOG_INF("  Target: ESP32-C3 | Sensors Only | LoRa IN865");
    LOG_INF("=================================================");

    /* Initialize Hardware Watchdog (30s timeout) */
    watchdog_init(WDT_TIMEOUT_MS);
    watchdog_feed();

    /* Initialize MCUboot & Image Validation */
    mcuboot_client_init();
    sigstore_verify_init();

    /* Initialize Local Storage (LittleFS) */
    littlefs_init();

    /* Initialize Power & Sleep */
    deep_sleep_init();
    solar_charger_init();

    /* Initialize Sensors */
    sht45_init();
    vwc_ec_init();
    leaf_wetness_init();
    rain_gauge_init();
    bh1750_init();
    battery_init();

    /* Initialize LoRa SX1262 */
    lora_sx1262_init();

    LOG_INF("All node subsystems initialized successfully. Entering telemetry loop.");

    while (1) {
        watchdog_feed();

        /* Assemble Telemetry Packet */
        memset(&current_pkt, 0, sizeof(current_pkt));
        current_pkt.timestamp = (uint32_t)(k_uptime_get() / 1000);
        current_pkt.seq_id = sequence_id++;
        get_device_mac(current_pkt.device_id);

        /* Read physical agricultural sensors */
        sht45_read(&current_pkt.temp_air, &current_pkt.rh);
        vwc_ec_read(&current_pkt.vwc, &current_pkt.ec, &current_pkt.temp_soil);
        leaf_wetness_read(&current_pkt.leaf_wet);
        current_pkt.rain_mm = rain_gauge_get_and_reset();
        bh1750_read(&current_pkt.par, &current_pkt.par);
        current_pkt.battery_mv = battery_read_mv();

        LOG_INF("Sampled [seq=%u]: AirTemp=%.1fC RH=%.1f%% SoilVWC=%.1f%% Rain=%.1fmm PAR=%.1f Bat=%umV",
                current_pkt.seq_id, current_pkt.temp_air, current_pkt.rh,
                current_pkt.vwc, current_pkt.rain_mm, current_pkt.par,
                current_pkt.battery_mv);

        /* Encode into compact CBOR */
        uint8_t cbor_buf[128];
        size_t cbor_len = 0;
        int ret = cbor_encode_sensor_packet(&current_pkt, cbor_buf, sizeof(cbor_buf), &cbor_len);
        if (ret != 0) {
            LOG_ERR("CBOR encoding failed (%d)", ret);
            continue;
        }

        /* Frame with FLIP protocol + CRC16 */
        uint8_t tx_frame[160];
        size_t frame_len = 0;
        ret = flip_protocol_frame(FLIP_MSG_TELEMETRY, current_pkt.seq_id, current_pkt.device_id,
                                  cbor_buf, (uint8_t)cbor_len, tx_frame, sizeof(tx_frame), &frame_len);

        /* Transmit via LoRa with retries */
        bool tx_success = false;
        for (int retry = 0; retry < MAX_TX_RETRIES; retry++) {
            watchdog_feed();
            ret = lora_sx1262_send(tx_frame, frame_len);
            if (ret == 0) {
                tx_success = true;
                LOG_INF("LoRa TX success (seq=%u, len=%zu bytes)", current_pkt.seq_id, frame_len);
                break;
            }
            LOG_WRN("LoRa TX attempt %d failed, retrying in 2s...", retry + 1);
            k_sleep(K_SECONDS(2));
        }

        /* If TX failed after all retries, buffer to LittleFS flash */
        if (!tx_success) {
            LOG_WRN("LoRa unavailable, buffering packet seq=%u to LittleFS", current_pkt.seq_id);
            littlefs_write_packet(&current_pkt);
            gateway_online = false;
        } else {
            /* Open receive window for Gateway ACK */
            uint8_t rx_buf[64];
            size_t rx_len = 0;
            int32_t rx_rssi = 0;
            int8_t rx_snr = 0;

            ret = lora_sx1262_recv(rx_buf, sizeof(rx_buf), &rx_len, &rx_rssi, &rx_snr, K_MSEC(500));
            if (ret == 0 && rx_len > 0) {
                current_pkt.rssi = (int8_t)rx_rssi;
                current_pkt.snr = rx_snr;
                process_gateway_response(rx_buf, rx_len);
            }
        }

        /* If Gateway link is responsive, flush buffered historical packets */
        if (gateway_online && littlefs_get_buffered_count() > 0) {
            LOG_INF("Replaying offline buffer: %zu packets queued in flash", littlefs_get_buffered_count());
            buffer_protocol_flush_batch(10);
        }

        /* Power down peripherals and enter deep sleep for configured cycle */
        watchdog_feed();
        LOG_INF("Entering low-power sleep for %d minutes...", SLEEP_INTERVAL_MIN);
        deep_sleep_enter_minutes(SLEEP_INTERVAL_MIN);
    }

    return 0;
}
