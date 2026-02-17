"""Unit tests for ProtocolService business logic."""

from django.test import TestCase

from modules.protocols.exceptions import (
    ProtocolNotFoundError,
    ProtocolValidationError,
)
from modules.protocols.services import ProtocolService


class ProtocolServiceCreateTest(TestCase):
    """Tests for ProtocolService.create_protocol validation rules."""

    def setUp(self):
        self.service = ProtocolService()

    def test_create_valid_protocol(self):
        data = {
            "title": "DNA Extraction",
            "description": "Standard protocol",
            "steps": "Step 1: collect sample",
        }
        protocol = self.service.create_protocol(data)
        self.assertEqual(protocol.title, "DNA Extraction")

    def test_create_rejects_empty_title(self):
        data = {
            "title": "   ",
            "description": "No title",
            "steps": "",
        }
        with self.assertRaises(ProtocolValidationError) as ctx:
            self.service.create_protocol(data)
        self.assertIn("title", ctx.exception.errors)


class ProtocolServiceGetTest(TestCase):
    """Tests for ProtocolService.get_protocol lookup."""

    def setUp(self):
        self.service = ProtocolService()

    def test_get_nonexistent_protocol_raises(self):
        with self.assertRaises(ProtocolNotFoundError):
            self.service.get_protocol(99999)


class ProtocolServiceUpdateTest(TestCase):
    """Tests for ProtocolService.update_protocol."""

    def setUp(self):
        self.service = ProtocolService()
        self.protocol = self.service.create_protocol(
            {
                "title": "Original",
                "description": "Desc",
                "steps": "Step 1",
            }
        )

    def test_update_valid_fields(self):
        updated = self.service.update_protocol(
            self.protocol.id, {"title": "Updated"}
        )
        self.assertEqual(updated.title, "Updated")

    def test_update_rejects_blank_title(self):
        with self.assertRaises(ProtocolValidationError):
            self.service.update_protocol(self.protocol.id, {"title": "   "})


class ProtocolServiceDeleteTest(TestCase):
    """Tests for ProtocolService.delete_protocol."""

    def setUp(self):
        self.service = ProtocolService()
        self.protocol = self.service.create_protocol(
            {
                "title": "To Delete",
                "description": "",
                "steps": "",
            }
        )

    def test_delete_existing_protocol(self):
        self.service.delete_protocol(self.protocol.id)
        with self.assertRaises(ProtocolNotFoundError):
            self.service.get_protocol(self.protocol.id)

    def test_delete_nonexistent_raises(self):
        with self.assertRaises(ProtocolNotFoundError):
            self.service.delete_protocol(99999)
