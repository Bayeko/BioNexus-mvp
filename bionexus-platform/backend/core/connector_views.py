"""API views for Plug-and-Parse connectors and AI mapping.

Endpoints:
- GET  /api/connectors/          → List all connectors
- GET  /api/connectors/{id}/     → Get connector details
- POST /api/mappings/suggest/    → AI suggests column mappings
- POST /api/mappings/confirm/    → User confirms mappings (saves to TenantConnectorProfile)
- GET  /api/tenant-profiles/     → Get saved profiles for current tenant
"""

import logging
from typing import Optional

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.ai_mapping_engine import get_mapping_engine
from core.models import Connector, ConnectorMapping, TenantConnectorProfile

logger = logging.getLogger(__name__)


@api_view(["GET"])
def list_connectors(request):
    """List all available connectors (SiLA 2 drivers).

    Response:
    [
        {
            "connector_id": "hamilton-microlab-star",
            "connector_name": "Hamilton Microlab STAR",
            "connector_type": "liquid_handler",
            "version": "1.0.0",
            "status": "active",
            "description": "...",
            "output_fields": [
                {"field_name": "dispense_volume", "data_type": "float", "unit": "μL", ...}
            ]
        },
        ...
    ]
    """
    connectors = Connector.objects.filter(status=Connector.ACTIVE)
    data = []

    for connector in connectors:
        fields = ConnectorMapping.objects.filter(
            connector=connector
        ).values()
        data.append(
            {
                "connector_id": connector.connector_id,
                "connector_name": connector.connector_name,
                "connector_type": connector.connector_type,
                "version": connector.version,
                "status": connector.status,
                "description": connector.description,
                "output_fields": list(fields),
            }
        )

    return Response(data)


@api_view(["GET"])
def get_connector(request, connector_id: str):
    """Get detailed connector info including FDL descriptor.

    Response:
    {
        "connector_id": "hamilton-microlab-star",
        "connector_name": "Hamilton Microlab STAR",
        "description": "...",
        "fdl_descriptor": {...},
        "pivot_model_mapping": {...},
        "output_fields": [...]
    }
    """
    connector = get_object_or_404(Connector, connector_id=connector_id)
    fields = ConnectorMapping.objects.filter(
        connector=connector
    ).values()

    return Response(
        {
            "connector_id": connector.connector_id,
            "connector_name": connector.connector_name,
            "description": connector.description,
            "connector_type": connector.connector_type,
            "version": connector.version,
            "status": connector.status,
            "fdl_descriptor": connector.fdl_descriptor,
            "pivot_model_mapping": connector.pivot_model_mapping,
            "output_fields": list(fields),
        }
    )


@api_view(["POST"])
def suggest_mappings(request):
    """AI suggests column mappings for incoming data.

    Request:
    {
        "incoming_columns": ["Temp", "Sample_ID", "Vol"],
        "connector_id": "hamilton-microlab-star"  # Optional, for context
    }

    Response:
    {
        "incoming_columns": ["Temp", "Sample_ID", "Vol"],
        "suggestions": {
            "Temp": {
                "pivot_field": "temperature",
                "confidence": 0.98,
                "description": "Temperature in Celsius"
            },
            "Sample_ID": {
                "pivot_field": "sample_id",
                "confidence": 0.95,
                "description": "Unique identifier for the sample"
            },
            "Vol": {
                "pivot_field": "volume",
                "confidence": 0.87,
                "description": "Volume in microliters"
            }
        },
        "summary": "AI suggested 3/3 mappings with high confidence"
    }
    """
    data = request.data
    incoming_columns = data.get("incoming_columns", [])
    connector_id = data.get("connector_id")

    if not incoming_columns:
        return Response(
            {"error": "incoming_columns is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get AI mapping engine
    engine = get_mapping_engine()

    # Get suggestions
    suggestions_result = engine.suggest_mappings(
        incoming_columns=incoming_columns,
        connector_id=connector_id,
    )

    # Enrich suggestions with Pivot Model details
    suggestions = {}
    for col, pivot_field in suggestions_result["high_confidence_mappings"].items():
        confidence = suggestions_result["confidences"][col]
        if pivot_field:
            pivot_info = engine.pivot_model.get(pivot_field, {})
            suggestions[col] = {
                "pivot_field": pivot_field,
                "confidence": confidence,
                "description": pivot_info.get("description", ""),
                "unit": pivot_info.get("unit", ""),
            }

    # Count suggestions
    high_confidence = len(suggestions)
    total = len(incoming_columns)

    return Response(
        {
            "incoming_columns": incoming_columns,
            "suggestions": suggestions,
            "summary": f"AI suggested {high_confidence}/{total} mappings with high confidence",
        }
    )


@api_view(["POST"])
def confirm_mappings(request):
    """User confirms mappings and saves to TenantConnectorProfile.

    Request:
    {
        "connector_id": "hamilton-microlab-star",
        "machine_instance_name": "Hamilton-Lab1",
        "column_mapping": {
            "Temp": "temperature",
            "Sample_ID": "sample_id",
            "Vol": "volume"
        },
        "mapping_confidence_scores": {
            "Temp": 0.98,
            "Sample_ID": 0.95,
            "Vol": 0.87
        }
    }

    Response:
    {
        "success": True,
        "tenant_profile_id": 123,
        "message": "Mapping saved for Hamilton-Lab1",
        "profile": {
            "machine_instance_name": "Hamilton-Lab1",
            "connector": "Hamilton Microlab STAR",
            "column_mapping": {...},
            "confirmed_at": "2024-01-15T10:30:00Z",
            "confirmed_by": "john.doe"
        }
    }
    """
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    data = request.data
    connector_id = data.get("connector_id")
    machine_instance_name = data.get("machine_instance_name")
    column_mapping = data.get("column_mapping", {})
    mapping_confidence_scores = data.get("mapping_confidence_scores", {})

    # Validate inputs
    if not connector_id or not machine_instance_name:
        return Response(
            {"error": "connector_id and machine_instance_name are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get connector
    try:
        connector = Connector.objects.get(connector_id=connector_id)
    except Connector.DoesNotExist:
        return Response(
            {"error": f"Connector not found: {connector_id}"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Get tenant
    tenant = request.user.tenant

    # Create or update TenantConnectorProfile
    profile, created = TenantConnectorProfile.objects.update_or_create(
        tenant=tenant,
        connector=connector,
        machine_instance_name=machine_instance_name,
        defaults={
            "column_mapping": column_mapping,
            "mapping_confidence_scores": mapping_confidence_scores,
            "confirmed_by": request.user,
            "confirmed_at": timezone.now(),
            "is_active": True,
        },
    )

    return Response(
        {
            "success": True,
            "tenant_profile_id": profile.id,
            "message": f"Mapping saved for {machine_instance_name}",
            "profile": {
                "id": profile.id,
                "machine_instance_name": profile.machine_instance_name,
                "connector": connector.connector_name,
                "column_mapping": profile.column_mapping,
                "mapping_confidence_scores": profile.mapping_confidence_scores,
                "confirmed_at": profile.confirmed_at.isoformat()
                if profile.confirmed_at
                else None,
                "confirmed_by": request.user.username,
                "is_active": profile.is_active,
            },
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET"])
def list_tenant_profiles(request):
    """List all connector profiles for the current tenant.

    Response:
    [
        {
            "id": 123,
            "machine_instance_name": "Hamilton-Lab1",
            "connector": "Hamilton Microlab STAR",
            "column_mapping": {...},
            "confirmed_at": "2024-01-15T10:30:00Z",
            "is_active": True
        },
        ...
    ]
    """
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    tenant = request.user.tenant
    profiles = TenantConnectorProfile.objects.filter(tenant=tenant).order_by(
        "-confirmed_at"
    )

    data = [
        {
            "id": p.id,
            "machine_instance_name": p.machine_instance_name,
            "connector": p.connector.connector_name,
            "connector_id": p.connector.connector_id,
            "column_mapping": p.column_mapping,
            "mapping_confidence_scores": p.mapping_confidence_scores,
            "confirmed_at": p.confirmed_at.isoformat()
            if p.confirmed_at
            else None,
            "confirmed_by": p.confirmed_by.username if p.confirmed_by else None,
            "is_active": p.is_active,
        }
        for p in profiles
    ]

    return Response(data)


@api_view(["DELETE"])
def deactivate_profile(request, profile_id: int):
    """Deactivate a tenant connector profile.

    Response:
    {
        "success": True,
        "message": "Profile deactivated"
    }
    """
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        profile = TenantConnectorProfile.objects.get(
            id=profile_id, tenant=request.user.tenant
        )
    except TenantConnectorProfile.DoesNotExist:
        return Response(
            {"error": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    profile.is_active = False
    profile.save()

    return Response(
        {"success": True, "message": "Profile deactivated"}
    )


# Import timezone for datetime operations
from django.utils import timezone
