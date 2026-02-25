"""Mapping Dynamique par IA - AI-powered column recognition and mapping.

When data arrives from a machine, this engine:
1. Recognizes what columns/fields are being sent
2. Compares them against the Pivot Model
3. Suggests mappings with confidence scores
4. Saves confirmed mappings to TenantConnectorProfile

This enables the "plug-and-play" behavior: users can add new machines without coding.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Pivot Model - the "golden standard" of all fields we know about
PIVOT_MODEL = {
    # Sample/Container Info
    "sample_id": {
        "description": "Unique identifier for the sample",
        "type": "string",
        "category": "sample",
    },
    "sample_name": {
        "description": "Human-readable sample name",
        "type": "string",
        "category": "sample",
    },
    "plate_id": {
        "description": "Plate/container identifier",
        "type": "string",
        "category": "sample",
    },
    "well_position": {
        "description": "Well position (e.g., 'A1', 'H12')",
        "type": "string",
        "category": "sample",
    },
    # Temperature & Environmental
    "temperature": {
        "description": "Temperature in Celsius",
        "type": "float",
        "unit": "°C",
        "category": "environment",
    },
    "humidity": {
        "description": "Relative humidity",
        "type": "float",
        "unit": "%",
        "category": "environment",
    },
    # Volume & Liquid Handling
    "volume": {
        "description": "Volume in microliters",
        "type": "float",
        "unit": "μL",
        "category": "liquid",
    },
    "dispensed_volume": {
        "description": "Volume dispensed by liquid handler",
        "type": "float",
        "unit": "μL",
        "category": "liquid",
    },
    "aspirated_volume": {
        "description": "Volume aspirated by liquid handler",
        "type": "float",
        "unit": "μL",
        "category": "liquid",
    },
    # Optical Measurements
    "absorbance": {
        "description": "Optical absorbance (OD600, OD405, etc.)",
        "type": "float",
        "category": "optical",
    },
    "fluorescence": {
        "description": "Fluorescence intensity",
        "type": "float",
        "category": "optical",
    },
    "luminescence": {
        "description": "Luminescence signal",
        "type": "float",
        "category": "optical",
    },
    # Molecular Biology
    "dna_concentration": {
        "description": "DNA concentration (ng/μL)",
        "type": "float",
        "unit": "ng/μL",
        "category": "molecular",
    },
    "ct_value": {
        "description": "Cycle threshold in qPCR",
        "type": "float",
        "category": "molecular",
    },
    "amplification_status": {
        "description": "PCR amplification detected (yes/no)",
        "type": "boolean",
        "category": "molecular",
    },
    # Time & Timestamp
    "timestamp": {
        "description": "Time of measurement",
        "type": "datetime",
        "category": "time",
    },
    "duration": {
        "description": "Duration of process",
        "type": "float",
        "unit": "seconds",
        "category": "time",
    },
    # Status & Quality
    "status": {
        "description": "Operation status (success, error, warning)",
        "type": "string",
        "category": "status",
    },
    "quality_flag": {
        "description": "Data quality assessment",
        "type": "string",
        "category": "status",
    },
}


class AIMappingEngine:
    """AI-powered column recognition and mapping to Pivot Model."""

    def __init__(self, threshold: float = 0.7):
        """Initialize mapping engine.

        Args:
            threshold: Minimum confidence score to auto-suggest a mapping (0-1)
        """
        self.threshold = threshold
        self.pivot_model = PIVOT_MODEL

    def suggest_mappings(
        self,
        incoming_columns: list[str],
        connector_id: Optional[str] = None,
    ) -> dict:
        """Suggest mappings for incoming columns to Pivot Model.

        Args:
            incoming_columns: List of column names from machine (e.g., ["Temp", "Vol"])
            connector_id: Optional connector ID for context (unused in v1, for future ML)

        Returns:
            Dict with suggested mappings and confidence scores:
            {
                "mappings": {
                    "Temp": "temperature",
                    "Vol": "volume",
                    "UnknownField": None  # Not confident
                },
                "confidences": {
                    "Temp": 0.98,
                    "Vol": 0.87,
                    "UnknownField": 0.32
                },
                "high_confidence_mappings": {
                    "Temp": "temperature",
                    "Vol": "volume"
                }
            }
        """
        mappings = {}
        confidences = {}
        high_confidence_mappings = {}

        for incoming_col in incoming_columns:
            score, pivot_field = self._find_best_match(incoming_col)
            confidences[incoming_col] = score

            if score >= self.threshold:
                mappings[incoming_col] = pivot_field
                high_confidence_mappings[incoming_col] = pivot_field
            else:
                mappings[incoming_col] = None

        return {
            "mappings": mappings,
            "confidences": confidences,
            "high_confidence_mappings": high_confidence_mappings,
        }

    def _find_best_match(self, incoming_col: str) -> tuple[float, Optional[str]]:
        """Find best matching Pivot Model field for an incoming column.

        Uses multiple strategies:
        1. Exact match (after normalization)
        2. Substring match
        3. Semantic similarity (word overlap)

        Args:
            incoming_col: Column name from machine

        Returns:
            Tuple of (confidence_score, pivot_field_name)
        """
        best_score = 0.0
        best_field = None

        normalized_incoming = incoming_col.lower().replace("_", "").replace(" ", "")

        for pivot_field in self.pivot_model.keys():
            score = 0.0

            # Strategy 1: Exact match (highest confidence)
            if normalized_incoming == pivot_field.lower():
                score = 1.0
            # Strategy 2: Exact substring (high confidence)
            elif (
                normalized_incoming in pivot_field.lower()
                or pivot_field.lower() in normalized_incoming
            ):
                score = 0.9
            # Strategy 3: Word overlap (medium confidence)
            else:
                score = self._calculate_word_overlap(incoming_col, pivot_field)

            if score > best_score:
                best_score = score
                best_field = pivot_field

        return best_score, best_field

    @staticmethod
    def _calculate_word_overlap(col1: str, col2: str) -> float:
        """Calculate similarity based on word/token overlap.

        Example: "temp_celsius" and "temperature" share "temp" → 0.5 similarity

        Args:
            col1: First column name
            col2: Second column name

        Returns:
            Similarity score (0.0 to 0.8)
        """
        # Split by common delimiters
        tokens1 = set(col1.lower().split("_"))
        tokens2 = set(col2.lower().split("_"))

        # Remove single characters (noise)
        tokens1 = {t for t in tokens1 if len(t) > 1}
        tokens2 = {t for t in tokens2 if len(t) > 1}

        if not tokens1 or not tokens2:
            return 0.0

        # Jaccard similarity
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        similarity = len(intersection) / len(union)

        return similarity * 0.8  # Cap at 0.8 to prioritize exact matches

    def validate_mapping(
        self,
        incoming_columns: list[str],
        suggested_mappings: dict,
        user_confirmed_mappings: dict,
    ) -> dict:
        """Validate user-confirmed mappings before saving to TenantConnectorProfile.

        Args:
            incoming_columns: Original columns from machine
            suggested_mappings: What the AI suggested
            user_confirmed_mappings: What the user actually confirmed

        Returns:
            Validation result:
            {
                "is_valid": True/False,
                "errors": [...],
                "confirmed_mappings": {...},
                "summary": "User confirmed 5/5 mappings, all valid"
            }
        """
        errors = []
        confirmed = {}

        for col, pivot_field in user_confirmed_mappings.items():
            # Validate column is in incoming columns
            if col not in incoming_columns:
                errors.append(f"Column '{col}' not in incoming data")
                continue

            # Validate pivot_field exists in Pivot Model (or is None for unmapped)
            if pivot_field is not None and pivot_field not in self.pivot_model:
                errors.append(
                    f"Unknown Pivot field: '{pivot_field}' "
                    f"(not in Pivot Model)"
                )
                continue

            confirmed[col] = pivot_field

        is_valid = len(errors) == 0
        total = len(incoming_columns)
        confirmed_count = len(confirmed)

        return {
            "is_valid": is_valid,
            "errors": errors,
            "confirmed_mappings": confirmed,
            "summary": (
                f"User confirmed {confirmed_count}/{total} mappings. "
                f"{'All valid.' if is_valid else f'{len(errors)} error(s) found.'}"
            ),
        }


# Singleton instance
_mapping_engine = None


def get_mapping_engine(threshold: float = 0.7) -> AIMappingEngine:
    """Get or create the global AIMappingEngine instance.

    Args:
        threshold: Minimum confidence for auto-suggestions

    Returns:
        AIMappingEngine singleton
    """
    global _mapping_engine
    if _mapping_engine is None:
        _mapping_engine = AIMappingEngine(threshold=threshold)
    return _mapping_engine
