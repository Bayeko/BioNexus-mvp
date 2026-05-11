#!/usr/bin/env python3
"""Simulate a lab instrument sending data to the BioNexus Box.

Sends realistic Mettler Toledo SICS balance frames via TCP socket
to box_collector.py running on the BioNexus Box (or localhost).

This replaces a real RS232/USB instrument for demo purposes.
When you have a real instrument, just plug it in — box_collector.py
reads the same data format from serial port instead of TCP.

Usage:
    # Send to Box at 192.168.10.134
    python simulate_instrument.py --host 192.168.10.134 --port 9600

    # Send to localhost (dev mode)
    python simulate_instrument.py

    # Fast mode (2x speed)
    python simulate_instrument.py --speed 2

    # Sartorius SBI format instead of Mettler SICS
    python simulate_instrument.py --protocol sbi

    # Generic CSV (pH meter)
    python simulate_instrument.py --protocol csv
"""

import argparse
import random
import socket
import sys
import time
from datetime import datetime


# ---------------------------------------------------------------------------
# Instrument Profiles
# ---------------------------------------------------------------------------

def mettler_sics_frames(count: int) -> list[str]:
    """Generate Mettler Toledo SICS weight readings.

    Real format: S S     12.3456 g
    S = response to SI command, S = stable, value, unit
    """
    frames = []
    base_weight = random.uniform(5.0, 50.0)

    for i in range(count):
        # Simulate slight weight drift (realistic for balance)
        weight = base_weight + random.gauss(0, 0.002)
        stability = "S" if random.random() > 0.1 else "D"  # 90% stable
        frames.append(f"S {stability}     {weight:10.4f} g")

    return frames


def sartorius_sbi_frames(count: int) -> list[str]:
    """Generate Sartorius SBI balance readings.

    Real format: +  100.0000 g
    """
    frames = []
    base_weight = random.uniform(10.0, 200.0)

    for i in range(count):
        weight = base_weight + random.gauss(0, 0.005)
        sign = "+" if weight >= 0 else "-"
        frames.append(f"{sign}  {abs(weight):10.4f} g")

    return frames


def csv_ph_frames(count: int) -> list[str]:
    """Generate generic CSV pH/temperature readings.

    Format: parameter,value,unit
    """
    frames = []
    base_ph = random.uniform(6.8, 7.6)
    base_temp = random.uniform(24.0, 26.0)

    for i in range(count):
        if i % 2 == 0:
            ph = base_ph + random.gauss(0, 0.05)
            frames.append(f"pH,{ph:.2f},pH")
        else:
            temp = base_temp + random.gauss(0, 0.3)
            frames.append(f"temperature,{temp:.1f},°C")

    return frames


def csv_spectro_frames(count: int) -> list[str]:
    """Generate spectrophotometer absorbance readings."""
    frames = []
    wavelengths = [260, 280, 340, 595]

    for i in range(count):
        wl = wavelengths[i % len(wavelengths)]
        abs_val = random.uniform(0.1, 2.5)
        frames.append(f"absorbance_{wl}nm,{abs_val:.6f},AU")

    return frames


def karl_fischer_frames(count: int) -> list[str]:
    """Generate Karl Fischer titrator result rows.

    Format : ``KF,water_content,<value>,%,<sample_id>,<volume_ml>,<drift>``
    Mirrors the CSV transfer-mode output of Mettler T-series and Metrohm
    KF titrators. Water content typically lands between 0.05 % and 5 %
    depending on sample type (pharma APIs are often in 0.1 to 2 %).
    """
    frames = []
    for i in range(count):
        water_content = random.uniform(0.05, 2.5)
        volume_ml = random.uniform(5.0, 20.0)
        drift = random.uniform(2.0, 8.0)
        sample = f"KF-Sample-{i + 1:03d}"
        frames.append(
            f"KF,water_content,{water_content:.3f},%,"
            f"{sample},{volume_ml:.2f},{drift:.1f}"
        )
    return frames


PROTOCOLS = {
    "sics": ("Mettler Toledo SICS (Balance)", mettler_sics_frames),
    "sbi": ("Sartorius SBI (Balance)", sartorius_sbi_frames),
    "csv": ("Generic CSV (pH Meter)", csv_ph_frames),
    "spectro": ("CSV Spectrophotometer", csv_spectro_frames),
    "kf": ("Karl Fischer Titrator", karl_fischer_frames),
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Simulate lab instrument → BioNexus Box",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host", default="localhost",
        help="BioNexus Box IP. Default: localhost",
    )
    parser.add_argument(
        "--port", type=int, default=9600,
        help="TCP port on Box. Default: 9600",
    )
    parser.add_argument(
        "--protocol", choices=PROTOCOLS.keys(), default="sics",
        help="Instrument protocol to simulate. Default: sics",
    )
    parser.add_argument(
        "--count", type=int, default=20,
        help="Number of readings to send. Default: 20",
    )
    parser.add_argument(
        "--speed", type=float, default=1.0,
        help="Speed multiplier (2 = 2x faster). Default: 1.0",
    )

    args = parser.parse_args()

    proto_name, frame_gen = PROTOCOLS[args.protocol]
    frames = frame_gen(args.count)

    base_delay = 3.0 / args.speed  # ~3 seconds between readings (realistic)

    print("=" * 60)
    print(f"BioNexus Instrument Simulator")
    print(f"Protocol:    {proto_name}")
    print(f"Target:      {args.host}:{args.port}")
    print(f"Readings:    {args.count}")
    print(f"Interval:    {base_delay:.1f}s")
    print("=" * 60)
    print()

    # Connect to Box
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((args.host, args.port))
        print(f"Connected to BioNexus Box at {args.host}:{args.port}")
        print()
    except ConnectionRefusedError:
        print(f"ERROR: Cannot connect to {args.host}:{args.port}")
        print("Is box_collector.py running on the Box?")
        sys.exit(1)

    # Send readings
    try:
        for i, frame in enumerate(frames, 1):
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"  [{timestamp}] ({i}/{args.count}) TX: {frame}")

            sock.sendall((frame + "\n").encode("utf-8"))

            if i < len(frames):
                # Add slight jitter (realistic instrument timing)
                delay = base_delay + random.uniform(-0.5, 0.5)
                time.sleep(max(0.5, delay))

        print()
        print(f"Done — {args.count} readings sent to BioNexus Box")
        print(f"Check the dashboard at http://localhost:3000")

    except KeyboardInterrupt:
        print(f"\nStopped after {i} readings")
    except BrokenPipeError:
        print(f"\nBox disconnected after {i} readings")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
