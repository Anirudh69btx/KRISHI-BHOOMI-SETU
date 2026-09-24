# FLIP Sensor Node Pinout Specification

**Microcontroller**: ESP32-C3-WROOM-02 / DevKitM (RISC-V 32-bit Single-Core, 160MHz)  
**Operating Voltage**: 3.3V DC (Regulated from 3.2V LiFePO4 battery via buck-boost)  
**Target Board Overlay**: `boards/esp32c3_devkitm.overlay`

---

## 1. Complete GPIO Mapping Table

| ESP32-C3 Pin | Function / Net Name | Type | Target Peripheral | Description |
|---|---|---|---|---|
| **GPIO0** | `ADC_SOIL_VWC` | Analog In | Capacitive Soil Probe | ADC0 Ch 0 (0-4095 counts, 0-3300mV) |
| **GPIO1** | `ADC_LEAF_WET` | Analog In | Dielectric Leaf Sensor | ADC0 Ch 1 (Surface moisture) |
| **GPIO2** | `SPI_MISO` | Digital In | SX1262 LoRa Module | SPI2 MISO |
| **GPIO3** | `ADC_BATT_DIV` | Analog In | Battery Voltage Divider | ADC0 Ch 3 (100k/100k divider, 2:1 ratio) |
| **GPIO4** | `I2C_SDA` | I2C Data | SHT45, BH1750, ATECC608B | 4.7kΩ pull-up to 3.3V |
| **GPIO5** | `I2C_SCL` | I2C Clock | SHT45, BH1750, ATECC608B | 4.7kΩ pull-up to 3.3V, 400kHz Fast Mode |
| **GPIO6** | `SPI_SCK` | Digital Out | SX1262 LoRa Module | SPI2 Clock (up to 10MHz) |
| **GPIO7** | `SPI_MOSI` | Digital Out | SX1262 LoRa Module | SPI2 MOSI |
| **GPIO8** | `RAIN_GAUGE_INT` | GPIO In | Tipping Bucket Reed Switch | Active Low, Internal Pull-up, Falling Edge IRQ |
| **GPIO9** | `LORA_DIO1` | GPIO In | SX1262 DIO1 Interrupt | Active High TX_DONE / RX_DONE interrupt |
| **GPIO10** | `LORA_NSS` | Digital Out | SX1262 Chip Select | Active Low SPI Chip Select |
| **GPIO18** | `LORA_BUSY` | GPIO In | SX1262 Busy Status | Active High (wait until low before SPI command) |
| **GPIO19** | `LORA_NRESET` | Digital Out | SX1262 Hardware Reset | Active Low |
| **GPIO20** | `UART_RXD` | UART In | CH340 / Programming | Console RX (115200 baud) |
| **GPIO21** | `UART_TXD` | UART Out | CH340 / Programming | Console TX (115200 baud) |

---

## 2. I2C Bus Address Map (GPIO4 / GPIO5)

| Device | I2C Address (7-bit Hex) | Part Number | Function |
|---|---|---|---|
| Air Temperature & Humidity | `0x44` | Sensirion SHT45-AD1B | ±0.1°C, ±1.0% RH |
| Ambient Light / Solar PAR | `0x23` | ROHM BH1750FVI | 1-65535 lux |
| Hardware Security Element | `0x60` | Microchip ATECC608B-TNG | X.509 certs, ECDSA P-256 |
| Real-Time Clock (Optional) | `0x68` | Maxim DS3231SN | ±2ppm TCXO RTC |

---

## 3. Power Distribution & Protection

- **V_IN (Solar)**: 6V / 10W panel input into CN3791 MPPT charger.
- **V_BATT**: LiFePO4 3.2V 5000mAh single cell with 2.5V undervoltage protection (DW01A + 8205A MOSFET).
- **3.3V System Rail**: High-efficiency buck-boost converter (TI TPS63001, 96% efficiency, <30µA quiescent).
- **TVS Protection**: Littlefuse SP0503BAHTG ESD protection arrays on all external sensor connectors.
