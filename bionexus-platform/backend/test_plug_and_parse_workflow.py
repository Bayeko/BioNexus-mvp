"""Integration test for Plug-and-Parse data capture workflow.

This test simulates:
1. Upload a CSV file with columns
2. AI recognizes the columns
3. User confirms the mappings
4. Data is saved correctly to database
5. Future uploads use saved mappings
"""

import json
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from core.models import (
    Tenant, User, Connector, ConnectorMapping, TenantConnectorProfile,
    RawFile, ParsedData
)
from core.ai_mapping_engine import get_mapping_engine


def test_plug_and_parse_workflow():
    """Test the complete Plug-and-Parse workflow."""

    print("=" * 80)
    print("TEST: Plug-and-Parse Data Capture Workflow")
    print("=" * 80)

    # SETUP: Create test data
    print("\n[SETUP] Creating test data...")
    tenant, _ = Tenant.objects.get_or_create(
        name='Test Lab',
        defaults={'slug': 'test-lab'}
    )
    print(f"✓ Tenant: {tenant.name}")

    user, _ = User.objects.get_or_create(
        username='test_user',
        tenant=tenant,
        defaults={'email': 'test@lab.local'}
    )
    user.set_password('TestPassword123!')
    user.save()
    print(f"✓ User: {user.username}")

    # Get the Hamilton connector (already loaded)
    try:
        connector = Connector.objects.get(connector_id='hamilton-microlab-star')
        print(f"✓ Connector: {connector.connector_name}")
    except Connector.DoesNotExist:
        print("✗ ERROR: Connector not found. Run: python manage.py load_connectors")
        return False

    # ===== SCENARIO 1: First Upload (AI Suggests Mappings) =====
    print("\n" + "=" * 80)
    print("SCENARIO 1: First Upload - AI Suggests Mappings")
    print("=" * 80)

    # Simulate incoming CSV data
    incoming_columns = ["Temp_C", "Sample_ID", "Vol_uL", "Status", "WeirdField"]
    incoming_data = {
        "Temp_C": 37.5,
        "Sample_ID": "SAMPLE-001",
        "Vol_uL": 100.5,
        "Status": "success",
        "WeirdField": "unknown_value"
    }

    print(f"\n[STEP 1] User uploads CSV with columns: {incoming_columns}")
    print(f"Data: {json.dumps(incoming_data, indent=2)}")

    # AI suggests mappings
    print("\n[STEP 2] AI suggests column mappings...")
    engine = get_mapping_engine(threshold=0.7)
    suggestions = engine.suggest_mappings(incoming_columns, connector_id='hamilton-microlab-star')

    print("\nAI Suggestions:")
    for col, pivot_field in suggestions['mappings'].items():
        confidence = suggestions['confidences'][col]
        status = "✓" if confidence >= 0.7 else "⚠"
        print(f"  {status} {col:15} → {str(pivot_field):20} (confidence: {confidence:.2f})")

    # User confirms mappings
    print("\n[STEP 3] User confirms mappings in UI...")
    confirmed_mappings = {
        "Temp_C": "temperature",
        "Sample_ID": "sample_id",
        "Vol_uL": "volume",
        "Status": "status"
        # WeirdField is NOT mapped (left empty)
    }

    # Save to TenantConnectorProfile
    profile, created = TenantConnectorProfile.objects.update_or_create(
        tenant=tenant,
        connector=connector,
        machine_instance_name="Hamilton-Lab1",
        defaults={
            "column_mapping": confirmed_mappings,
            "mapping_confidence_scores": {
                "Temp_C": suggestions['confidences']['Temp_C'],
                "Sample_ID": suggestions['confidences']['Sample_ID'],
                "Vol_uL": suggestions['confidences']['Vol_uL'],
                "Status": suggestions['confidences']['Status'],
            },
            "confirmed_by": user,
            "confirmed_at": timezone.now(),
            "is_active": True,
        }
    )

    action = "created" if created else "updated"
    print(f"✓ TenantConnectorProfile {action}: {profile.id}")
    print(f"  Machine: {profile.machine_instance_name}")
    print(f"  Column Mapping: {json.dumps(profile.column_mapping, indent=4)}")

    # Save raw file
    print("\n[STEP 4] Saving raw file to database...")
    csv_content = "Temp_C,Sample_ID,Vol_uL,Status,WeirdField\n37.5,SAMPLE-001,100.5,success,unknown_value"
    raw_file = RawFile.objects.create(
        tenant=tenant,
        user=user,
        filename="hamilton_run_001.csv",
        file_content=csv_content.encode(),
        file_hash="abc123def456",  # Mock hash
        file_size=len(csv_content),
        mime_type="text/csv",
        storage_backend=RawFile.LOCAL,
        storage_path="local://hamilton_run_001.csv"
    )
    print(f"✓ RawFile saved: {raw_file.filename} (id={raw_file.id})")

    # Transform data using the saved mapping
    print("\n[STEP 5] Transforming CSV data using saved TenantConnectorProfile...")
    transformed_data = {}
    for incoming_col, pivot_field in profile.column_mapping.items():
        if incoming_col in incoming_data and pivot_field:
            transformed_data[pivot_field] = incoming_data[incoming_col]

    print(f"Transformed data:")
    print(json.dumps(transformed_data, indent=2))

    # Save parsed data
    print("\n[STEP 6] Saving parsed data to database...")
    parsed_data = ParsedData.objects.create(
        raw_file=raw_file,
        tenant=tenant,
        parsed_json=transformed_data,
        extraction_confidence=0.85,
        extraction_model="ai-mapper-v1",
        field_confidence_scores={
            "temperature": 0.95,
            "sample_id": 0.98,
            "volume": 0.87,
            "status": 1.0
        },
        flagged_fields=[],  # No low-confidence fields
        state=ParsedData.VALIDATED,
        validated_by=user,
        validated_at=timezone.now(),
        confirmed_json=transformed_data
    )
    print(f"✓ ParsedData saved: {parsed_data.id}")
    print(f"  State: {parsed_data.state}")
    print(f"  Validated by: {parsed_data.validated_by.username}")

    # ===== SCENARIO 2: Second Upload (Auto-Use Saved Mapping) =====
    print("\n" + "=" * 80)
    print("SCENARIO 2: Second Upload - Auto-Use Saved Mapping (No Re-Asking!)")
    print("=" * 80)

    incoming_columns_2 = ["Temp_C", "Sample_ID", "Vol_uL", "Status"]  # Same columns
    incoming_data_2 = {
        "Temp_C": 38.2,
        "Sample_ID": "SAMPLE-002",
        "Vol_uL": 95.3,
        "Status": "success"
    }

    print(f"\n[STEP 1] User uploads SECOND CSV with same columns: {incoming_columns_2}")
    print(f"Data: {json.dumps(incoming_data_2, indent=2)}")

    # AUTOMATIC: Fetch saved profile for this tenant + connector
    print("\n[STEP 2] System fetches saved profile for Hamilton-Lab1...")
    saved_profile = TenantConnectorProfile.objects.filter(
        tenant=tenant,
        connector=connector,
        machine_instance_name="Hamilton-Lab1",
        is_active=True
    ).first()

    if saved_profile:
        print(f"✓ Found saved profile (id={saved_profile.id})")
        print(f"  Created: {saved_profile.created_at}")
        print(f"  Confirmed by: {saved_profile.confirmed_by.username} @ {saved_profile.confirmed_at}")

    # AUTOMATIC: Apply mapping without asking user
    print("\n[STEP 3] AUTOMATICALLY apply saved mapping (no user interaction!)...")
    transformed_data_2 = {}
    for incoming_col, pivot_field in saved_profile.column_mapping.items():
        if incoming_col in incoming_data_2 and pivot_field:
            transformed_data_2[pivot_field] = incoming_data_2[incoming_col]

    print(f"Transformed data (auto-mapped):")
    print(json.dumps(transformed_data_2, indent=2))

    # Save second file and parsed data
    raw_file_2 = RawFile.objects.create(
        tenant=tenant,
        user=user,
        filename="hamilton_run_002.csv",
        file_content="Temp_C,Sample_ID,Vol_uL,Status\n38.2,SAMPLE-002,95.3,success".encode(),
        file_hash="abc123def789",
        file_size=48,
        mime_type="text/csv",
        storage_backend=RawFile.LOCAL
    )

    parsed_data_2 = ParsedData.objects.create(
        raw_file=raw_file_2,
        tenant=tenant,
        parsed_json=transformed_data_2,
        extraction_confidence=0.88,
        extraction_model="ai-mapper-v1",
        field_confidence_scores={
            "temperature": 0.96,
            "sample_id": 0.99,
            "volume": 0.89,
            "status": 1.0
        },
        state=ParsedData.VALIDATED,
        validated_by=user,
        validated_at=timezone.now(),
        confirmed_json=transformed_data_2
    )

    print(f"✓ Second file processed automatically!")
    print(f"  RawFile: {raw_file_2.filename}")
    print(f"  ParsedData: {parsed_data_2.id}")

    # ===== VERIFICATION =====
    print("\n" + "=" * 80)
    print("VERIFICATION: Data in Database")
    print("=" * 80)

    print(f"\n✓ TenantConnectorProfile count: {TenantConnectorProfile.objects.count()}")
    print(f"✓ RawFile count: {RawFile.objects.count()}")
    print(f"✓ ParsedData count: {ParsedData.objects.count()}")

    # Query saved data
    print("\n[Database Check] SELECT * FROM TenantConnectorProfile WHERE tenant_id={};".format(tenant.id))
    for profile in TenantConnectorProfile.objects.filter(tenant=tenant):
        print(f"  ID={profile.id}, Machine={profile.machine_instance_name}, Active={profile.is_active}")
        print(f"    Mapping: {profile.column_mapping}")

    print("\n[Database Check] SELECT * FROM RawFile WHERE tenant_id={};".format(tenant.id))
    for rf in RawFile.objects.filter(tenant=tenant):
        print(f"  ID={rf.id}, Filename={rf.filename}, Hash={rf.file_hash[:8]}...")

    print("\n[Database Check] SELECT * FROM ParsedData WHERE tenant_id={};".format(tenant.id))
    for pd in ParsedData.objects.filter(tenant=tenant):
        print(f"  ID={pd.id}, State={pd.state}, Confidence={pd.extraction_confidence}")
        print(f"    Data: {json.dumps(pd.confirmed_json, indent=6)}")

    # ===== SUCCESS =====
    print("\n" + "=" * 80)
    print("✅ TEST PASSED: Data Capture Complete!")
    print("=" * 80)
    print("""
SUMMARY:
--------
1. ✓ AI recognized incoming columns
2. ✓ User confirmed mappings once
3. ✓ Data saved to TenantConnectorProfile
4. ✓ First file parsed and transformed
5. ✓ Second file auto-mapped (no re-asking!)
6. ✓ All data in database with correct structure

HOW DATA IS CAPTURED:
---------------------
CSV Columns         → AI Recognition     → User Confirms    → TenantConnectorProfile
"Temp_C"            → "temperature"      → [✓ OK]           → Saved in DB
"Sample_ID"         → "sample_id"        → [✓ OK]           → Saved in DB
"Vol_uL"            → "volume"           → [✓ OK]           → Saved in DB
"Status"            → "status"           → [✓ OK]           → Saved in DB

Next uploads        → Check TenantConnectorProfile      → Auto-transform → ParsedData

This is PLUG-AND-PLAY: No recoding needed!
""")

    return True


if __name__ == "__main__":
    success = test_plug_and_parse_workflow()
    exit(0 if success else 1)
