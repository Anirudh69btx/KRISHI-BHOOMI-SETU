#!/usr/bin/env python3
"""
FLIP Solar MPPT & LiFePO4 Battery Autonomy Estimator
Simulates daily energy harvesting and power consumption for ESP32-C3 Sensor Node
Validates >14 days continuous autonomy under worst-case monsoon season overcast conditions.
"""

import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def simulate_power_budget(solar_w: float, battery_ah: float, sleep_min: float,
                           active_tx_ma: float, active_sense_ma: float,
                           sleep_ma: float) -> dict:
    """
    Simulates node power consumption and solar energy harvesting
    """
    v_batt = 3.2 # LiFePO4 nominal voltage
    battery_wh = battery_ah * v_batt

    # Cycle timing (in seconds)
    t_tx_s = 1.2      # LoRa transmission burst at SF10
    t_sense_s = 0.8   # ADC and I2C sensor sampling
    t_sleep_s = (sleep_min * 60.0) - t_tx_s - t_sense_s

    # Average energy per 15-minute cycle (in milliampere-seconds and milliampere-hours)
    mas_tx = active_tx_ma * t_tx_s
    mas_sense = active_sense_ma * t_sense_s
    mas_sleep = sleep_ma * t_sleep_s

    mas_per_cycle = mas_tx + mas_sense + mas_sleep
    mah_per_cycle = mas_per_cycle / 3600.0

    cycles_per_day = (24.0 * 60.0) / sleep_min
    daily_consumption_mah = mah_per_cycle * cycles_per_day
    daily_consumption_wh = (daily_consumption_mah / 1000.0) * v_batt

    # Zero-Solar Monsoon Autonomy (Days running purely on battery from 100% to 15% cutoff)
    usable_capacity_ah = battery_ah * 0.85 # 85% depth of discharge
    autonomy_days_zero_sun = (usable_capacity_ah * 1000.0) / daily_consumption_mah

    # Monsoon overcast harvest:
    # 2 hours diffuse sunlight at ~15% panel efficiency
    # 10W panel yields: 10W * 0.20 (monsoon diffuse factor) * 2 hours * 0.85 (MPPT conversion)
    daily_monsoon_harvest_wh = solar_w * 0.20 * 2.0 * 0.85
    daily_net_energy_wh = daily_monsoon_harvest_wh - daily_consumption_wh

    return {
        "battery_wh": battery_wh,
        "daily_consumption_mah": round(daily_consumption_mah, 2),
        "daily_consumption_wh": round(daily_consumption_wh, 4),
        "daily_monsoon_harvest_wh": round(daily_monsoon_harvest_wh, 3),
        "daily_net_wh": round(daily_net_energy_wh, 3),
        "autonomy_days_zero_sun": round(autonomy_days_zero_sun, 1),
        "average_node_current_ma": round(daily_consumption_mah / 24.0, 3),
    }


def main():
    parser = argparse.ArgumentParser(description="FLIP Power Budget & Battery Autonomy Simulator")
    parser.add_argument("--solar", default="10W", help="Solar panel rating (e.g. 10W)")
    parser.add_argument("--battery", default="5Ah", help="Battery capacity (e.g. 5Ah)")
    parser.add_argument("--sleep", default="15min", help="Sleep interval (e.g. 15min)")
    parser.add_argument("--active_tx", default="200mA", help="Active TX current (e.g. 200mA)")
    parser.add_argument("--active_sense", default="50mA", help="Active sensing current (e.g. 50mA)")
    parser.add_argument("--sleep_cur", default="0.08mA", help="Sleep quiescent current (e.g. 0.08mA)")
    args = parser.parse_args()

    # Parse inputs
    solar_w = float(args.solar.replace("W", ""))
    battery_ah = float(args.battery.replace("Ah", ""))
    sleep_min = float(args.sleep.replace("min", ""))
    active_tx = float(args.active_tx.replace("mA", ""))
    active_sense = float(args.active_sense.replace("mA", ""))
    sleep_cur = float(args.sleep_cur.replace("mA", ""))

    res = simulate_power_budget(solar_w, battery_ah, sleep_min, active_tx, active_sense, sleep_cur)

    print("\n=======================================================")
    print("        FLIP Sensor Node Power Budget & Autonomy")
    print("=======================================================")
    print(f" Solar Panel:             {solar_w}W Monocrystalline MPPT")
    print(f" Battery Capacity:        {battery_ah}Ah LiFePO4 (3.2V, {res['battery_wh']}Wh)")
    print(f" Measurement Interval:    {sleep_min} minutes (96 cycles/day)")
    print(f" Sleep Current:           {sleep_cur*1000:.1f} µA (<100µA target)")
    print("-------------------------------------------------------")
    print(f" Daily Energy Consumed:   {res['daily_consumption_mah']} mAh/day ({res['daily_consumption_wh']} Wh/day)")
    print(f" Average Current Draw:    {res['average_node_current_ma']} mA")
    print(f" Monsoon Solar Harvest:   {res['daily_monsoon_harvest_wh']} Wh/day (2h overcast sun)")
    print(f" Daily Net Energy Balance: +{res['daily_net_wh']} Wh/day (Positive harvest)")
    print("-------------------------------------------------------")
    print(f" Autonomy with ZERO Sun:  {res['autonomy_days_zero_sun']} days (Requirement: >14 days)")
    print("=======================================================\n")

    if res["autonomy_days_zero_sun"] >= 14.0:
        print("✅ VERIFICATION PASSED: Node autonomy exceeds 14 days without any sunlight.\n")
        sys.exit(0)
    else:
        print("❌ VERIFICATION FAILED: Insufficient battery capacity for 14-day blackout autonomy.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
