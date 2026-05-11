#!/usr/bin/env python
"""BioNexus Equipment Simulator — Generates realistic lab data for demos.

Simulates laboratory instruments connected via the BioNexus Box gateway.
Creates instruments, samples, measurements with SHA-256 data hashes,
and populates the audit trail — exactly like a real deployment.

Usage:
    python simulate_equipment.py                  # Interactive menu
    python simulate_equipment.py --auto           # Full demo (all instruments)
    python simulate_equipment.py --equipment pcr  # Single instrument
    python simulate_equipment.py --live           # LIVE DEMO — real-time data flow
    python simulate_equipment.py --live --speed 2 # Live demo, 2x faster
"""

import os
import sys
import json
import time
import random
import hashlib
import argparse
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.utils import timezone
from core.models import Tenant, User, AuditLog
from core.audit import AuditTrail
from modules.instruments.models import Instrument
from modules.samples.models import Sample
from modules.measurements.models import Measurement
from modules.protocols.models import Protocol


# =============================================================================
# Instrument Profiles — Realistic lab instruments
# =============================================================================

INSTRUMENT_PROFILES = {
    "spectrophotometer": {
        "name": "Shimadzu UV-2600i Spectrophotometer",
        "instrument_type": "spectrophotometer",
        "serial_number": "SN-UV2600-2024-0891",
        "connection_type": "USB",
    },
    "pcr": {
        "name": "Bio-Rad CFX96 Real-Time PCR",
        "instrument_type": "pcr_machine",
        "serial_number": "SN-CFX96-2023-4521",
        "connection_type": "Ethernet",
    },
    "plate_reader": {
        "name": "Tecan Spark 10M Plate Reader",
        "instrument_type": "plate_reader",
        "serial_number": "SN-SPARK-2024-7832",
        "connection_type": "Ethernet",
    },
    "ph_meter": {
        "name": "Mettler Toledo SevenExcellence pH Meter",
        "instrument_type": "ph_meter",
        "serial_number": "SN-MT7E-2024-1190",
        "connection_type": "RS232",
    },
    "hplc": {
        "name": "Agilent 1260 Infinity II HPLC",
        "instrument_type": "hplc",
        "serial_number": "SN-AG1260-2023-5567",
        "connection_type": "Ethernet",
    },
}


# =============================================================================
# Measurement Generators — What each instrument measures
# =============================================================================

MEASUREMENT_PROFILES = {
    "spectrophotometer": [
        {"parameter": "absorbance_260nm", "unit": "AU", "min": 0.05, "max": 3.0},
        {"parameter": "absorbance_280nm", "unit": "AU", "min": 0.03, "max": 2.5},
        {"parameter": "absorbance_230nm", "unit": "AU", "min": 0.02, "max": 2.0},
        {"parameter": "concentration", "unit": "ng/uL", "min": 5.0, "max": 500.0},
    ],
    "pcr": [
        {"parameter": "ct_value", "unit": "cycles", "min": 12.0, "max": 38.0},
        {"parameter": "melt_temperature", "unit": "°C", "min": 75.0, "max": 95.0},
        {"parameter": "fluorescence_rfu", "unit": "RFU", "min": 100.0, "max": 50000.0},
    ],
    "plate_reader": [
        {"parameter": "absorbance_450nm", "unit": "OD", "min": 0.01, "max": 4.0},
        {"parameter": "fluorescence_485_535", "unit": "RFU", "min": 50.0, "max": 100000.0},
        {"parameter": "luminescence", "unit": "RLU", "min": 10.0, "max": 500000.0},
    ],
    "ph_meter": [
        {"parameter": "pH", "unit": "pH", "min": 2.0, "max": 12.0},
        {"parameter": "temperature", "unit": "°C", "min": 15.0, "max": 37.0},
        {"parameter": "conductivity", "unit": "mS/cm", "min": 0.1, "max": 50.0},
    ],
    "hplc": [
        {"parameter": "retention_time", "unit": "min", "min": 1.5, "max": 25.0},
        {"parameter": "peak_area", "unit": "mAU*s", "min": 100.0, "max": 500000.0},
        {"parameter": "peak_height", "unit": "mAU", "min": 5.0, "max": 2000.0},
        {"parameter": "resolution", "unit": "", "min": 1.0, "max": 15.0},
    ],
}


# =============================================================================
# Sample Templates — Realistic biological samples
# =============================================================================

SAMPLE_BATCHES = [
    {"prefix": "BLD", "batch": "BATCH-2026-001", "names": [
        "Patient Alpha - Whole Blood", "Patient Beta - Venous Blood",
        "Patient Gamma - Capillary Blood", "QC Control - Normal Range",
    ]},
    {"prefix": "PLS", "batch": "BATCH-2026-002", "names": [
        "Patient Alpha - EDTA Plasma", "Patient Beta - Citrate Plasma",
        "QC Control - High Level", "QC Control - Low Level",
    ]},
    {"prefix": "DNA", "batch": "BATCH-2026-003", "names": [
        "Sample A - Genomic DNA", "Sample B - Plasmid DNA",
        "Positive Control - Reference", "Negative Control - NTC",
    ]},
    {"prefix": "SER", "batch": "BATCH-2026-004", "names": [
        "Patient Delta - Fasting Serum", "Patient Epsilon - Post-Prandial",
        "Calibrator Level 1", "Calibrator Level 2",
    ]},
    {"prefix": "RNA", "batch": "BATCH-2026-005", "names": [
        "Tissue Biopsy - Total RNA", "Cell Culture - mRNA Extract",
        "QC Reference RNA", "Patient Zeta - Circulating RNA",
    ]},
]

PROTOCOLS = [
    {"title": "UV-Vis Absorbance (260/280nm)", "description": "Nucleic acid purity assessment via spectrophotometry.", "steps": "1. Blank instrument\n2. Load sample\n3. Measure A260\n4. Measure A280\n5. Calculate ratio"},
    {"title": "qPCR Gene Expression", "description": "Real-time PCR quantification of target gene expression.", "steps": "1. Prepare master mix\n2. Load plate\n3. Thermal cycling\n4. Analyze Ct values\n5. Calculate ΔΔCt"},
    {"title": "ELISA Protein Quantification", "description": "Sandwich ELISA for cytokine or biomarker quantification.", "steps": "1. Coat plate\n2. Block\n3. Add samples/standards\n4. Detection antibody\n5. Read OD450"},
    {"title": "pH & Conductivity Check", "description": "Buffer and media QC using pH and conductivity meters.", "steps": "1. Calibrate pH probe\n2. Measure sample pH\n3. Measure temperature\n4. Record conductivity"},
    {"title": "HPLC Purity Analysis", "description": "Reverse-phase HPLC for compound purity assessment.", "steps": "1. Equilibrate column\n2. Inject sample\n3. Run gradient\n4. Analyze peaks\n5. Calculate purity %"},
]


# =============================================================================
# Core Simulation Logic
# =============================================================================

def clean_demo_data():
    """Delete all demo data for a fresh start. Keeps instruments."""
    print("\n  Cleaning demo data for fresh start...")
    m_count = Measurement.objects.count()
    Measurement.objects.all().delete()
    print(f"  Deleted {m_count} measurements")

    s_count = Sample.objects.count()
    Sample.objects.all().delete()
    print(f"  Deleted {s_count} samples")

    a_count = AuditLog.objects.count()
    AuditLog.objects.all().delete()
    print(f"  Deleted {a_count} audit records")

    p_count = Protocol.objects.count()
    Protocol.objects.all().delete()
    print(f"  Deleted {p_count} protocols")

    print("  Demo data cleaned! Instruments preserved.\n")


def get_or_create_tenant():
    tenant, created = Tenant.objects.get_or_create(
        slug="demo-lab",
        defaults={"name": "BioNexus Demo Laboratory", "description": "Demo lab for BioNexus MVP"},
    )
    return tenant


def get_or_create_user(tenant):
    try:
        return User.objects.get(username="demo_user", tenant=tenant)
    except User.DoesNotExist:
        print("  [!] demo_user not found. Run: python create_demo_user.py")
        sys.exit(1)


def create_instrument(profile_key):
    """Create or get an instrument from profile."""
    profile = INSTRUMENT_PROFILES[profile_key]
    instrument, created = Instrument.objects.get_or_create(
        serial_number=profile["serial_number"],
        defaults={
            "name": profile["name"],
            "instrument_type": profile["instrument_type"],
            "connection_type": profile["connection_type"],
            "status": "online",
        },
    )
    if not created and instrument.status != "online":
        instrument.status = "online"
        instrument.save(update_fields=["status"])

    action = "Created" if created else "Found"
    print(f"  [{action}] Instrument: {instrument.name} ({instrument.status})")
    return instrument


def create_samples(instrument, user, count=4):
    """Create realistic biological samples linked to instrument."""
    batch_template = random.choice(SAMPLE_BATCHES)
    samples = []

    for i in range(min(count, len(batch_template["names"]))):
        sample_id = f"{batch_template['prefix']}-{random.randint(10000, 99999)}"
        name = batch_template["names"][i]

        sample, created = Sample.objects.get_or_create(
            sample_id=sample_id,
            defaults={
                "instrument": instrument,
                "batch_number": batch_template["batch"],
                "status": "pending",
                "created_by": user.username,
            },
        )
        samples.append(sample)
        action = "Created" if created else "Found"
        print(f"  [{action}] Sample: {sample_id} — {name}")

    return samples


def create_protocol():
    proto = random.choice(PROTOCOLS)
    protocol, created = Protocol.objects.get_or_create(
        title=proto["title"],
        defaults={"description": proto["description"], "steps": proto["steps"]},
    )
    action = "Created" if created else "Found"
    print(f"  [{action}] Protocol: {protocol.title}")
    return protocol


def generate_measurements(instrument, samples, instrument_key, live_delay=0):
    """Generate realistic measurements with SHA-256 data hashes.

    Args:
        live_delay: Seconds between each measurement (0 = instant, >0 = real-time).
    """
    profiles = MEASUREMENT_PROFILES[instrument_key]
    measurements = []
    total = len(samples) * len(profiles)
    count = 0

    for i, sample in enumerate(samples):
        # Update sample status
        sample.status = "in_progress"
        sample.save(update_fields=["status"])

        if live_delay > 0:
            print(f"\n  >> Sample {i+1}/{len(samples)}: {sample.sample_id} — Analyzing...")
            sys.stdout.flush()

        for j, profile in enumerate(profiles):
            value = round(random.uniform(profile["min"], profile["max"]), 6)
            measured_at = timezone.now()

            measurement = Measurement.objects.create(
                sample=sample,
                instrument=instrument,
                parameter=profile["parameter"],
                value=Decimal(str(value)),
                unit=profile["unit"],
                measured_at=measured_at,
            )
            measurements.append(measurement)
            count += 1

            if live_delay > 0:
                # Live mode: print each measurement as it arrives
                print(f"     [{count}/{total}] {profile['parameter']} = {value} {profile['unit']}  "
                      f"(SHA-256: {measurement.data_hash[:16]}...)")
                sys.stdout.flush()

                # Record audit immediately for each measurement
                AuditTrail.record(
                    entity_type="Measurement",
                    entity_id=measurement.id,
                    operation="CREATE",
                    changes={
                        "parameter": {"before": None, "after": measurement.parameter},
                        "value": {"before": None, "after": str(measurement.value)},
                        "data_hash": {"before": None, "after": measurement.data_hash[:16] + "..."},
                    },
                    snapshot_before={},
                    snapshot_after={
                        "sample_id": measurement.sample_id,
                        "instrument_id": measurement.instrument_id,
                        "parameter": measurement.parameter,
                        "value": str(measurement.value),
                        "unit": measurement.unit,
                        "data_hash": measurement.data_hash,
                    },
                    user_id=_live_user.id if _live_user else 1,
                    user_email=_live_user.email if _live_user else "",
                )

                # Wait between measurements — this is where the magic happens
                time.sleep(live_delay)

        # Mark sample complete
        sample.status = "completed"
        sample.save(update_fields=["status"])

        if live_delay > 0:
            print(f"  >> Sample {sample.sample_id} — COMPLETED")
            sys.stdout.flush()

    return measurements


# Global ref for live mode audit recording inside generate_measurements
_live_user = None


def record_audit_trail(user, instrument, samples, measurements):
    """Record audit events for the simulation."""
    # Instrument connection
    AuditTrail.record(
        entity_type="Instrument",
        entity_id=instrument.id,
        operation="UPDATE",
        changes={"status": {"before": "offline", "after": "online"}},
        snapshot_before={"status": "offline"},
        snapshot_after={"status": "online", "name": instrument.name},
        user_id=user.id,
        user_email=user.email,
    )

    # Each measurement
    for m in measurements:
        AuditTrail.record(
            entity_type="Measurement",
            entity_id=m.id,
            operation="CREATE",
            changes={
                "parameter": {"before": None, "after": m.parameter},
                "value": {"before": None, "after": str(m.value)},
                "data_hash": {"before": None, "after": m.data_hash[:16] + "..."},
            },
            snapshot_before={},
            snapshot_after={
                "sample_id": m.sample_id,
                "instrument_id": m.instrument_id,
                "parameter": m.parameter,
                "value": str(m.value),
                "unit": m.unit,
                "data_hash": m.data_hash,
            },
            user_id=user.id,
            user_email=user.email,
        )


def simulate_instrument(instrument_key, auto=False, live_delay=0):
    """Run full simulation for one instrument.

    Args:
        live_delay: If > 0, runs in live mode with delays between measurements.
    """
    global _live_user
    profile = INSTRUMENT_PROFILES[instrument_key]
    is_live = live_delay > 0

    if is_live:
        print(f"\n{'='*60}")
        print(f"  LIVE SIMULATION: {profile['name']}")
        print(f"  Data will appear in real-time on the dashboard")
        print(f"  Open http://localhost:3000 to watch")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"  SIMULATING: {profile['name']}")
        print(f"{'='*60}\n")

    tenant = get_or_create_tenant()
    user = get_or_create_user(tenant)
    _live_user = user

    # Step 1: Connect instrument
    if is_live:
        print("[1/4] BioNexus Box connecting to instrument...")
        time.sleep(live_delay * 0.5)
    else:
        print("[1/5] Connecting instrument...")
    instrument = create_instrument(instrument_key)

    if is_live:
        # Record instrument connection audit
        AuditTrail.record(
            entity_type="Instrument",
            entity_id=instrument.id,
            operation="UPDATE",
            changes={"status": {"before": "offline", "after": "online"}},
            snapshot_before={"status": "offline"},
            snapshot_after={"status": "online", "name": instrument.name},
            user_id=user.id,
            user_email=user.email,
        )
        print(f"  >> Instrument ONLINE via {profile['connection_type']}")
        time.sleep(live_delay)

    # Step 2: Register samples
    if is_live:
        print(f"\n[2/4] Receiving samples from {profile['name']}...")
        time.sleep(live_delay * 0.5)
    else:
        print("\n[2/5] Registering samples...")
    samples = create_samples(instrument, user, count=4)

    if is_live:
        time.sleep(live_delay)

    # Step 3: Link protocol
    if not is_live:
        print("\n[3/5] Loading protocol...")
    protocol = create_protocol()

    # Step 4: Generate measurements — the main show for live mode
    num_params = len(MEASUREMENT_PROFILES[instrument_key])
    total_measurements = len(samples) * num_params

    if is_live:
        print(f"\n[3/4] Running analysis — {total_measurements} measurements incoming...")
        print(f"       Watch the dashboard update in real-time!")
        print(f"       ({len(samples)} samples x {num_params} parameters)")
    else:
        print(f"\n[4/5] Running {profile['name']}...")

    measurements = generate_measurements(instrument, samples, instrument_key, live_delay=live_delay)

    if not is_live:
        print(f"  Generated {len(measurements)} measurements")
        for m in measurements[:3]:
            print(f"    {m.parameter} = {m.value} {m.unit} (hash: {m.data_hash[:12]}...)")
        if len(measurements) > 3:
            print(f"    ... and {len(measurements) - 3} more")

    # Step 5: Record audit trail (only for non-live — live records inline)
    if not is_live:
        print(f"\n[5/5] Recording audit trail...")
        record_audit_trail(user, instrument, samples, measurements)

    if is_live:
        print(f"\n[4/4] All data received and hashed.")

    audit_count = AuditLog.objects.count()

    # Summary
    print(f"\n{'='*60}")
    print(f"  SIMULATION COMPLETE")
    print(f"{'='*60}")
    print(f"  Instrument:    {instrument.name}")
    print(f"  Connection:    {profile['connection_type']} via BioNexus Box")
    print(f"  Samples:       {len(samples)}")
    print(f"  Measurements:  {len(measurements)}")
    print(f"  Audit Records: {audit_count}")
    if is_live:
        print(f"  Data Integrity: All {len(measurements)} measurements SHA-256 hashed")
    print(f"{'='*60}\n")

    return measurements


def run_full_demo(live_delay=0):
    """Run complete demo with all instruments."""
    is_live = live_delay > 0

    print("\n" + "=" * 60)
    if is_live:
        print("  BIONEXUS LIVE DEMO")
        print("  Real-time data flow from 5 laboratory instruments")
        print("  Open the dashboard and watch data appear live!")
    else:
        print("  BIONEXUS FULL DEMO SCENARIO")
        print("  Simulating a complete laboratory workflow")
    print("=" * 60)

    if is_live:
        print("\n  Starting in 3 seconds — switch to the dashboard now!")
        for i in range(3, 0, -1):
            print(f"  {i}...")
            time.sleep(1)

    for key in INSTRUMENT_PROFILES:
        simulate_instrument(key, live_delay=live_delay)
        if is_live:
            print("\n  Next instrument in 2 seconds...\n")
            time.sleep(2)

    # Final stats
    print("\n" + "=" * 60)
    print("  DEMO COMPLETE")
    print("=" * 60)
    print(f"  Instruments:   {Instrument.objects.count()}")
    print(f"  Samples:       {Sample.objects.count()}")
    print(f"  Protocols:     {Protocol.objects.count()}")
    print(f"  Measurements:  {Measurement.objects.count()}")
    print(f"  Audit Records: {AuditLog.objects.count()}")
    print("=" * 60)
    print("\n  Open http://localhost:3000 to see the dashboard!\n")


def run_live_demo(speed=1.0, equipment=None, no_prompt=False):
    """Run live demo with real-time delays.

    Args:
        speed: Speed multiplier (1.0 = normal ~3s between measurements,
               2.0 = fast ~1.5s, 0.5 = slow ~6s).
        equipment: Specific instrument key or None for all.
        no_prompt: Skip the "Press ENTER" prompt (for .bat calls).
    """
    base_delay = 3.0 / speed  # 3 seconds per measurement at normal speed

    print("\n" + "=" * 60)
    print("  BIONEXUS LIVE DEMO MODE")
    print("=" * 60)
    print(f"  Speed:    {'Normal' if speed == 1 else f'{speed}x'} ({base_delay:.1f}s per measurement)")
    print(f"  Frontend: http://localhost:3000")
    print("=" * 60)

    if not no_prompt:
        print(f"  Tip:      Open the dashboard BEFORE pressing Enter!")
        input("\n  Press ENTER to start the live demo...")
    else:
        print("\n  Starting in 3 seconds — switch to the dashboard!")
        for i in range(3, 0, -1):
            print(f"  {i}...")
            time.sleep(1)

    if equipment:
        simulate_instrument(equipment, live_delay=base_delay)
    else:
        run_full_demo(live_delay=base_delay)


def interactive_menu():
    print("\n" + "=" * 60)
    print("  BIONEXUS EQUIPMENT SIMULATOR")
    print("=" * 60)
    print()
    print("  Choose a mode:\n")
    keys = list(INSTRUMENT_PROFILES.keys())
    print("  --- LIVE DEMO (real-time, for client demos) ---")
    print("  L. LIVE DEMO — All instruments (watch dashboard update!)")
    print()
    print("  --- INSTANT (batch load, for testing) ---")
    for i, key in enumerate(keys, 1):
        print(f"  {i}. {INSTRUMENT_PROFILES[key]['name']}")
    print(f"  {len(keys)+1}. FULL BATCH (all instruments, instant)")
    print("  0. Exit")
    print()

    choice = input("  Your choice: ").strip().upper()

    if choice == "L":
        run_live_demo(speed=1.0)
    elif choice == str(len(keys) + 1):
        run_full_demo()
    elif choice == "0":
        print("  Bye!")
    elif choice.isdigit() and 1 <= int(choice) <= len(keys):
        simulate_instrument(keys[int(choice) - 1])
    else:
        print("  Invalid choice.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BioNexus Equipment Simulator")
    parser.add_argument("--auto", action="store_true", help="Run full demo (instant batch)")
    parser.add_argument("--live", action="store_true", help="LIVE DEMO: real-time data flow")
    parser.add_argument("--clean", action="store_true",
                        help="Clean all demo data before starting (fresh start)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Live demo speed multiplier (default: 1.0, use 2 for faster)")
    parser.add_argument("--no-prompt", action="store_true",
                        help="Skip interactive prompts (for .bat launcher)")
    parser.add_argument("--equipment", choices=INSTRUMENT_PROFILES.keys(),
                        help="Simulate specific instrument")
    args = parser.parse_args()

    if args.clean:
        clean_demo_data()

    if args.live:
        run_live_demo(speed=args.speed, equipment=args.equipment, no_prompt=args.no_prompt)
    elif args.auto:
        run_full_demo()
    elif args.equipment:
        simulate_instrument(args.equipment)
    elif not args.clean:
        interactive_menu()
