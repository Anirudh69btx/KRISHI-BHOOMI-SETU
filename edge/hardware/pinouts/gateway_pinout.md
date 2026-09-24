# FLIP Edge Gateway Pinout Specification

**Compute Engine**: Raspberry Pi Zero 2W (Broadcom BCM2710A1 Quad-Core Cortex-A53 @ 1.0GHz, 512MB LPDDR2)  
**Host Operating System**: Ubuntu Core 22 (A/B system partitions) / Debian Bullseye  
**Carrier Interface**: 40-pin GPIO Header, CSI-2 Camera Ribbon, Micro-USB OTG

---

## 1. 40-Pin GPIO Header Mapping

| Physical Pin | BCM GPIO | Header Name | Connected Subsystem | Description |
|---|---|---|---|---|
| **Pin 1** | — | `3V3` | Logic Power | 3.3V System Logic Rail |
| **Pin 2** | — | `5V` | Primary Power | 5V DC from UPS HAT (3A capacity) |
| **Pin 3** | GPIO 2 | `SDA1` | I2C Bus | INA219 Power Monitor, DS3231 RTC (`0x68`) |
| **Pin 4** | — | `5V` | Primary Power | 5V DC tied to Pin 2 |
| **Pin 5** | GPIO 3 | `SCL1` | I2C Bus | I2C Clock (100kHz) |
| **Pin 6** | — | `GND` | Ground | System Ground |
| **Pin 8** | GPIO 14 | `TXD0` | UART0 | SIM7600 4G Modem AT Command Port TX |
| **Pin 10** | GPIO 15 | `RXD0` | UART0 | SIM7600 4G Modem AT Command Port RX |
| **Pin 12** | GPIO 18 | `PCM_CLK` | I2S Audio | SPH0645 MEMS Microphone BCLK / MAX98357A Amp |
| **Pin 17** | — | `3V3` | Logic Power | 3.3V Logic |
| **Pin 19** | GPIO 10 | `SPI0_MOSI` | LoRa HAT | SX1302 LoRa Concentrator SPI Data In |
| **Pin 21** | GPIO 9 | `SPI0_MISO` | LoRa HAT | SX1302 LoRa Concentrator SPI Data Out |
| **Pin 22** | GPIO 25 | `LORA_RST` | LoRa HAT | SX1302 Hardware Reset (Active High) |
| **Pin 23** | GPIO 11 | `SPI0_SCLK` | LoRa HAT | SX1302 SPI Clock (up to 8MHz) |
| **Pin 24** | GPIO 8 | `SPI0_CE0` | LoRa HAT | SX1302 SPI Chip Select 0 |
| **Pin 35** | GPIO 19 | `PCM_FS` | I2S Audio | Audio Word Select (LRCLK) |
| **Pin 38** | GPIO 20 | `PCM_DIN` | I2S Audio | SPH0645 MEMS Mic Data Out into Pi |
| **Pin 40** | GPIO 21 | `PCM_DOUT` | I2S Audio | MAX98357A 5W Audio Amp Data into Speaker |

---

## 2. Dedicated Peripheral Ports

- **CSI-2 Camera Port**: 15-pin FFC connected to Raspberry Pi Camera Module 3 (12MP Sony IMX708, Autofocus, Wide Angle 120° FOV).
- **Micro-USB OTG Data**: Connected to SIM7600 4G LTE USB interface for high-speed PPP/QMI network streaming (`wwan0`/`cdc-wdm0`).
- **Power Delivery**: 12V→5V 10A buck converter feeding Pi Zero 2W Pin 2/4 and 4G modem burst load.
