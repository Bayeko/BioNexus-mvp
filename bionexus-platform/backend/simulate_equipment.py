#!/usr/bin/env python
"""BioNexus Equipment Simulator — Generates realistic lab data for demos.

Simulates laboratory instruments connected via the BioNexus Box gateway.
Creates instruments, samples, measurements with SHA-256 data hashes,
and populates the audit trail — exactly like a real deployment.

Usage:
    python simulate_equipment.py                  # Interactive menu
    python simulate_equipment.py --auto           # Full demo (all instruments)
    python simulate_equipment.py --equipment pcr  # Single instrument
"""

import os
import sys
import json
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


def generate_measurements(instrument, samples, instrument_key):
    """Generate realistic measurements with SHA-256 data hashes."""
    profiles = MEASUREMENT_PROFILES[instrument_key]
    measurements = []
    base_time = timezone.now() - timedelta(minutes=random.randint(5, 60))

    for i, sample in enumerate(samples):
        # Update sample status
        sample.status = "in_progress"
        sample.save(update_fields=["status"])

        for j, profile in enumerate(profiles):
            value = round(random.uniform(profile["min"], profile["max"]), 6)
            measured_at = base_time + timedelta(seconds=(i * len(profiles) + j) * 30)

            measurement = Measurement.objects.create(
                sample=sample,
                instrument=instrument,
                parameter=profile["parameter"],
                value=Decimal(str(value)),
                unit=profile["unit"],
                measured_at=measured_at,
            )
            measurements.append(measurement)

        # Mark sample complete
        sample.status = "completed"
        sample.save(update_fields=["status"])

    return measurements


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


def simulate_instrument(instrument_key, auto=False):
    """Run full simulation for one instrument."""
    profile = INSTRUMENT_PROFILES[instrument_key]

    print(f"\n{'='*60}")
    print(f"  SIMULATING: {profile['name']}")
    print(f"{'='*60}\n")

    tenant = get_or_create_tenant()
    user = get_or_create_user(tenant)

    # Step 1: Connect instrument
    print("[1/5] Connecting instrument...")
    instrument = create_instrument(instrument_key)

    # Step 2: Register samples
    print("\n[2/5] Registering samples...")
    samples = create_samples(instrument, user, count=4)

    # Step 3: Link protocol
    print("\n[3/5] Loading protocol...")
    protocol = create_protocol()

    # Step 4: Generate measurements
    print(f"\n[4/5] Running {profile['name']}...")
    measurements = generate_measurements(instrument, samples, instrument_key)
    print(f"  Generated {len(measurements)} measurements")
    for m in measurements[:3]:
        print(f"    {m.parameter} = {m.value} {m.unit} (hash: {m.data_hash[:12]}...)")
    if len(measurements) > 3:
        print(f"    ... and {len(measurements) - 3} more")

    # Step 5: Record audit trail
    print(f"\n[5/5] Recording audit trail...")
    record_audit_trail(user, instrument, samples, measurements)
    audit_count = AuditLog.objects.count()
    print(f"  {audit_count} audit records total (SHA-256 chain)")

    # Summary
    print(f"\n{'='*60}")
    print(f"  SIMULATION COMPLETE")
    print(f"{'='*60}")
    print(f"  Instrument:    {instrument.name}")
    print(f"  Samples:       {len(samples)}")
    print(f"  Measurements:  {len(measurements)}")
    print(f"  Audit Records: {audit_count}")
    print(f"{'='*60}\n")

    return measurements


def run_full_demo():
    """Run complete demo with all instruments."""
    print("\n" + "=" * 60)
    print("  BIONEXUS FULL DEMO SCENARIO")
    print("  Simulating a complete laboratory workflow")
    print("=" * 60)

    for key in INSTRUMENT_PROFILES:
        simulate_instrument(key)

    # Final stats
    print("\n" + "=" * 60)
    print("  DEMO SUMMARY")
    print("=" * 60)
    print(f"  Instruments:   {Instrument.objects.count()}")
    print(f"  Samples:       {Sample.objects.count()}")
    print(f"  Protocols:     {Protocol.objects.count()}")
    print(f"  Measurements:  {Measurement.objects.count()}")
    print(f"  Audit Records: {AuditLog.objects.count()}")
    print("=" * 60)
    print("\n  Open http://localhost:5173 to see the dashboard!\n")


def interactive_menu():
    print("\n" + "=" * 60)
    print("  BIONEXUS EQUIPMENT SIMULATOR")
    print("=" * 60)
    print()
    print("  Choose an instrument to simulate:\n")
    keys = list(INSTRUMENT_PROFILES.keys())
    for i, key in enumerate(keys, 1):
        print(f"  {i}. {INSTRUMENT_PROFILES[key]['name']}")
    print(f"  {len(keys)+1}. FULL DEMO (all instruments)")
    print("  0. Exit")
    print()

    choice = input("  Your choice: ").strip()

    if choice == str(len(keys) + 1):
        run_full_demo()
    elif choice == "0":
        print("  Bye!")
    elif choice.isdigit() and 1 <= int(choice) <= len(keys):
        simulate_instrument(keys[int(choice) - 1])
    else:
        print("  Invalid choice.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BioNexus Equipment Simulator")
    parser.add_argument("--auto", action="store_true", help="Run full demo automatically")
    parser.add_argument("--equipment", choices=INSTRUMENT_PROFILES.keys(), help="Simulate specific instrument")
    args = parser.parse_args()

    if args.auto:
        run_full_demo()
    elif args.equipment:
        simulate_instrument(args.equipment)
    else:
        interactive_menu()
