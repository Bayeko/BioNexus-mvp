from django.test import TestCase
from modules.compliance.models import Compliance

class ComplianceModelTest(TestCase):
    def setUp(self):
        Compliance.objects.create(name="Test Compliance", description="Description here.")

    def test_compliance_creation(self):
        compliance = Compliance.objects.get(name="Test Compliance")
        self.assertEqual(compliance.description, "Description here.")
