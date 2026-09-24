cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(flip_sensor_node)

# Target sources
target_sources(app PRIVATE
    src/main.c
    src/sensors/sht45.c
    src/sensors/vwc_ec.c
    src/sensors/leaf_wetness.c
    src/sensors/rain_gauge.c
    src/sensors/bh1750.c
    src/sensors/battery.c
    src/comms/lora_sx1262.c
    src/comms/mqtt_sn.c
    src/comms/protocol.c
    src/storage/littlefs_manager.c
    src/storage/buffer_protocol.c
    src/ota/mcuboot_client.c
    src/ota/sigstore_verify.c
    src/power/deep_sleep.c
    src/power/solar_charger.c
    src/power/watchdog.c
    src/utils/cbor_codec.c
    src/utils/crc16.c
)

# Target include directories
target_include_directories(app PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/src/sensors
    ${CMAKE_CURRENT_SOURCE_DIR}/src/comms
    ${CMAKE_CURRENT_SOURCE_DIR}/src/storage
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ota
    ${CMAKE_CURRENT_SOURCE_DIR}/src/power
    ${CMAKE_CURRENT_SOURCE_DIR}/src/utils
)
