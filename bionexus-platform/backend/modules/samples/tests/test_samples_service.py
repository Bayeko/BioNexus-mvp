"""Unit tests for SampleService business logic.

These tests validate that the service layer enforces business rules
independently of the HTTP layer (views) and the database layer
(repository).
"""

from django.test import TestCase
from django.utils import timezone

from modules.samples.exceptions import SampleNotFoundError, SampleValidationError
from modules.samples.services import SampleService


class SampleServiceCreateTest(TestCase):
    """Tests for SampleService.create_sample validation rules."""

    def setUp(self):
        self.service = SampleService()

    def test_create_valid_sample(self):
        data = {
            "name": "Sample A",
            "sample_type": "blood",
            "received_at": timezone.now(),
            "location": "Freezer 1",
        }
        sample = self.service.create_sample(data)
        self.assertEqual(sample.name, "Sample A")
        self.assertEqual(sample.sample_type, "blood")

    def test_create_rejects_empty_name(self):
        data = {
            "name": "   ",
            "sample_type": "blood",
            "received_at": timezone.now(),
            "location": "Freezer 1",
        }
        with self.assertRaises(SampleValidationError) as ctx:
            self.service.create_sample(data)
        self.assertIn("name", ctx.exception.errors)

    def test_create_rejects_invalid_sample_type(self):
        data = {
            "name": "Sample B",
            "sample_type": "unknown_type",
            "received_at": timezone.now(),
            "location": "Freezer 1",
        }
        with self.assertRaises(SampleValidationError) as ctx:
            self.service.create_sample(data)
        self.assertIn("sample_type", ctx.exception.errors)

    def test_create_accepts_all_valid_types(self):
        for sample_type in ("blood", "plasma", "serum", "urine", "tissue", "dna", "rna"):
            data = {
                "name": f"Sample {sample_type}",
                "sample_type": sample_type,
                "received_at": timezone.now(),
                "location": "Freezer 1",
            }
            sample = self.service.create_sample(data)
            self.assertEqual(sample.sample_type, sample_type)


class SampleServiceGetTest(TestCase):
    """Tests for SampleService.get_sample lookup."""

    def setUp(self):
        self.service = SampleService()

    def test_get_nonexistent_sample_raises(self):
        with self.assertRaises(SampleNotFoundError):
            self.service.get_sample(99999)


class SampleServiceUpdateTest(TestCase):
    """Tests for SampleService.update_sample."""

    def setUp(self):
        self.service = SampleService()
        self.sample = self.service.create_sample(
            {
                "name": "Original",
                "sample_type": "blood",
                "received_at": timezone.now(),
                "location": "Freezer 1",
            }
        )

    def test_update_valid_fields(self):
        updated = self.service.update_sample(self.sample.id, {"name": "Updated"})
        self.assertEqual(updated.name, "Updated")

    def test_update_rejects_invalid_type(self):
        with self.assertRaises(SampleValidationError):
            self.service.update_sample(self.sample.id, {"sample_type": "invalid"})


class SampleServiceDeleteTest(TestCase):
    """Tests for SampleService.delete_sample."""

    def setUp(self):
        self.service = SampleService()
        self.sample = self.service.create_sample(
            {
                "name": "To Delete",
                "sample_type": "blood",
                "received_at": timezone.now(),
                "location": "Freezer 1",
            }
        )

    def test_delete_existing_sample(self):
        self.service.delete_sample(self.sample.id)
        with self.assertRaises(SampleNotFoundError):
            self.service.get_sample(self.sample.id)

    def test_delete_nonexistent_raises(self):
        with self.assertRaises(SampleNotFoundError):
            self.service.delete_sample(99999)
