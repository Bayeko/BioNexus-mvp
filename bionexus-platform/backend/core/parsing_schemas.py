"""Pydantic schemas for strict data validation (no hallucinations from AI).

These schemas define EXACTLY what the AI is allowed to extract.
Any deviation raises ValidationError immediately.

ALCOA+ Principle: Accuracy
- Strict types prevent silent type coercion
- Required fields enforce completeness
- Field constraints (min_length, regex) ensure data quality
- Custom validators add business logic
"""

from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class EquipmentData(BaseModel):
    """Schema for laboratory equipment data extraction.

    Example of what the AI is ALLOWED to extract from an equipment file.
    """

    equipment_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique equipment identifier",
    )
    equipment_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Equipment name/model",
    )
    equipment_type: str = Field(
        ...,
        pattern="^(centrifuge|spectrophotometer|incubator|microscope|pcr_machine|freezer|other)$",
        description="Equipment category (strict enum)",
    )
    location: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Physical location in lab",
    )
    serial_number: Optional[str] = Field(
        None,
        max_length=100,
        description="Equipment serial number",
    )
    purchase_date: Optional[str] = Field(
        None,
        description="Purchase date (ISO format: YYYY-MM-DD)",
    )
    last_maintenance: Optional[str] = Field(
        None,
        description="Last maintenance date (ISO format: YYYY-MM-DD)",
    )
    status: str = Field(
        "operational",
        pattern="^(operational|maintenance|broken|decommissioned)$",
        description="Equipment status",
    )
    notes: str = Field(
        "",
        max_length=1000,
        description="Additional notes",
    )

    @field_validator("purchase_date", "last_maintenance", mode="before")
    @classmethod
    def validate_dates(cls, v):
        """Validate date format (ISO 8601)."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                datetime.fromisoformat(v)
                return v
            except ValueError:
                raise ValueError(f"Invalid date format: {v}. Use YYYY-MM-DD")
        raise ValueError("Date must be string in ISO format")

    model_config = {
        "extra": "forbid",  # ❌ REJECT extra fields (no hallucinations)
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }


class SampleData(BaseModel):
    """Schema for sample data extraction from lab files."""

    sample_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique sample identifier",
    )
    sample_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )
    sample_type: str = Field(
        ...,
        pattern="^(blood|plasma|serum|urine|tissue|dna|rna|other)$",
        description="Sample biological type",
    )
    collected_at: str = Field(
        ...,
        description="Collection timestamp (ISO format)",
    )
    collected_by: Optional[str] = Field(
        None,
        max_length=255,
        description="Person who collected sample",
    )
    storage_temperature: Optional[int] = Field(
        None,
        ge=-196,  # Liquid nitrogen
        le=25,    # Room temp
        description="Storage temperature in Celsius",
    )
    storage_location: Optional[str] = Field(
        None,
        max_length=255,
        description="Where sample is stored",
    )
    quantity: Optional[float] = Field(
        None,
        gt=0,
        description="Sample quantity",
    )
    quantity_unit: Optional[str] = Field(
        None,
        pattern="^(ml|mg|µl|g|other)$",
        description="Unit of quantity",
    )
    notes: str = Field(
        "",
        max_length=1000,
    )

    @field_validator("collected_at", mode="before")
    @classmethod
    def validate_timestamp(cls, v):
        """Validate ISO timestamp."""
        try:
            datetime.fromisoformat(v)
            return v
        except (ValueError, TypeError):
            raise ValueError(f"Invalid timestamp: {v}. Use ISO 8601 format")

    model_config = {
        "extra": "forbid",
        "str_strip_whitespace": True,
    }


class BatchExtractionResult(BaseModel):
    """Container for multiple extracted entities from one file."""

    equipment_records: list[EquipmentData] = Field(
        default_factory=list,
        max_items=1000,
        description="Equipment entries extracted",
    )
    sample_records: list[SampleData] = Field(
        default_factory=list,
        max_items=1000,
        description="Sample entries extracted",
    )
    extraction_warnings: list[str] = Field(
        default_factory=list,
        description="Warnings from AI (e.g., 'skipped row 42: invalid type')",
    )

    model_config = {
        "extra": "forbid",
    }
