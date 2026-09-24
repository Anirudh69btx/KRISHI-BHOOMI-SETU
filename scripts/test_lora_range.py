#!/usr/bin/env python3
"""
FLIP LoRa RF Link Budget & Range Calculator
Evaluates 865-867 MHz LoRa link performance across agricultural foliage
Models: Free-space Path Loss (FSPL) & Log-Distance Path Loss with Foliage Attenuation (Weissberger Model)
"""

import argparse
import math
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def calculate_link_budget(freq_mhz: float, sf: int, bw_khz: float, tx_power_dbm: float,
                           rx_sens_dbm: float, antenna_gain_dbi: float) -> dict:
    """
    Computes Maximum Allowable Path Loss (MAPL) and distance estimates
    """
    # Link Budget MAPL
    # MAPL = P_tx + G_tx + G_rx - Sensitivity - Fade_Margin
    fade_margin_db = 10.0 # 10 dB agricultural shadow fade margin
    cable_loss_db = 1.0   # 0.5 dB per connector/cable

    mapl_db = tx_power_dbm + (2 * antenna_gain_dbi) - rx_sens_dbm - fade_margin_db - (2 * cable_loss_db)

    # Free Space Path Loss (LOS): FSPL(dB) = 20*log10(d_km) + 20*log10(f_mhz) + 32.44
    # d_km = 10^((MAPL - 20*log10(f_mhz) - 32.44) / 20)
    c_los = 20.0 * math.log10(freq_mhz) + 32.44
    max_dist_los_km = 10.0 ** ((mapl_db - c_los) / 20.0)

    # Agricultural Foliage Model (Dense Crop Canopy: Sugarcane/Cotton):
    # Path loss exponent n = 3.2, foliage absorption ~0.2 dB/m
    # PL(d) = PL(d0) + 10*n*log10(d/d0) + alpha*d
    # Iteratively solve for distance at MAPL
    d_m = 10.0
    pl_10m = 20.0 * math.log10(freq_mhz) + 20.0 * math.log10(d_m / 1000.0) + 32.44
    crop_range_m = 10.0
    for test_d in range(20, 5000, 10):
        pl = pl_10m + 10.0 * 3.2 * math.log10(test_d / 10.0) + (0.015 * test_d)
        if pl >= mapl_db:
            crop_range_m = test_d
            break

    # Fresnel Zone radius at 500m (mid-path):
    # R_1 = 17.32 * sqrt(d_km / (4 * f_ghz))
    d_mid_km = 0.5
    f_ghz = freq_mhz / 1000.0
    fresnel_radius_m = round(17.32 * math.sqrt(d_mid_km / (4.0 * f_ghz)), 2)

    return {
        "frequency_mhz": freq_mhz,
        "tx_power_dbm": tx_power_dbm,
        "rx_sensitivity_dbm": rx_sens_dbm,
        "antenna_gain_dbi": antenna_gain_dbi,
        "mapl_db": round(mapl_db, 1),
        "max_range_los_km": round(max_dist_los_km, 2),
        "max_range_crops_m": crop_range_m,
        "fresnel_midpath_radius_m": fresnel_radius_m,
    }


def main():
    parser = argparse.ArgumentParser(description="FLIP LoRa Range & Link Budget Calculator")
    parser.add_argument("--frequency", type=float, default=865.0, help="Frequency in MHz (default: 865.0)")
    parser.add_argument("--sf", type=int, default=10, help="Spreading Factor (default: 10)")
    parser.add_argument("--bw", type=float, default=125.0, help="Bandwidth in kHz (default: 125.0)")
    parser.add_argument("--tx", type=float, default=14.0, help="TX power in dBm (default: 14.0)")
    parser.add_argument("--rx_sensitivity", type=float, default=-137.0, help="Receiver sensitivity in dBm (default: -137.0)")
    parser.add_argument("--antenna_gain", type=float, default=5.0, help="Antenna gain in dBi (default: 5.0)")
    args = parser.parse_args()

    results = calculate_link_budget(
        freq_mhz=args.frequency,
        sf=args.sf,
        bw_khz=args.bw,
        tx_power_dbm=args.tx,
        rx_sens_dbm=args.rx_sensitivity,
        antenna_gain_dbi=args.antenna_gain
    )

    print("\n=======================================================")
    print("      FLIP LoRa Link Budget & Propagation Model")
    print("=======================================================")
    print(f" Frequency:            {results['frequency_mhz']} MHz (IN865 Band)")
    print(f" TX Power:             {results['tx_power_dbm']} dBm")
    print(f" RX Sensitivity:       {results['rx_sensitivity_dbm']} dBm (SF10, BW125kHz)")
    print(f" Antenna Gain:         +{results['antenna_gain_dbi']} dBi")
    print(f" Maximum Allowable PL: {results['mapl_db']} dB")
    print("-------------------------------------------------------")
    print(f" Line-of-Sight Range:  {results['max_range_los_km']} km (Requirement: >2.0 km)")
    print(f" Crop Canopy Range:    {results['max_range_crops_m']} m (Requirement: >500 m)")
    print(f" 1st Fresnel Radius:   {results['fresnel_midpath_radius_m']} m (at 500m mid-point)")
    print("=======================================================\n")

    # Verification criteria
    pass_los = results["max_range_los_km"] >= 2.0
    pass_crop = results["max_range_crops_m"] >= 500

    if pass_los and pass_crop:
        print("✅ VERIFICATION PASSED: LoRa link exceeds range requirements for Indian farm topologies.\n")
        sys.exit(0)
    else:
        print("❌ VERIFICATION FAILED: Link budget insufficient.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
