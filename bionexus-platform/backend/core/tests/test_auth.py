"""Tests for JWT authentication and RBAC."""

from django.test import TestCase

from core.jwt_service import JWTService
from core.models import Permission, Role, Tenant, User


class JWTServiceTest(TestCase):
    """Tests for JWT token generation and verification."""

    def setUp(self):
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Lab",
            slug="test-lab",
        )

        # Create role
        self.role = Role.objects.create(name=Role.LAB_TECHNICIAN)

        # Create user
        self.user = User.objects.create_user(
            username="john.doe",
            email="john@lab.local",
            password="password123",
            tenant=self.tenant,
            role=self.role,
        )

    def test_generate_tokens(self):
        """JWT token generation returns valid tokens."""
        tokens = JWTService.generate_tokens(self.user)

        self.assertIn("access", tokens)
        self.assertIn("refresh", tokens)
        self.assertEqual(tokens["user_id"], self.user.id)
        self.assertEqual(tokens["tenant_id"], self.tenant.id)

    def test_verify_access_token(self):
        """Access token verification succeeds with valid token."""
        tokens = JWTService.generate_tokens(self.user)
        payload = JWTService.verify_token(tokens["access"], token_type="access")

        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], self.user.id)
        self.assertEqual(payload["role"], Role.LAB_TECHNICIAN)

    def test_verify_refresh_token(self):
        """Refresh token verification succeeds with valid token."""
        tokens = JWTService.generate_tokens(self.user)
        payload = JWTService.verify_token(
            tokens["refresh"], token_type="refresh"
        )

        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], self.user.id)

    def test_verify_wrong_token_type(self):
        """Verifying access token as refresh token fails."""
        tokens = JWTService.generate_tokens(self.user)
        payload = JWTService.verify_token(
            tokens["access"], token_type="refresh"
        )

        self.assertIsNone(payload)

    def test_invalid_token_verification_fails(self):
        """Invalid token returns None."""
        payload = JWTService.verify_token("invalid.token.here", "access")
        self.assertIsNone(payload)


class UserPermissionsTest(TestCase):
    """Tests for user permission checking."""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Lab",
            slug="test-lab",
        )

        # Create permissions
        Permission.objects.create(codename=Permission.SAMPLE_VIEW)
        Permission.objects.create(codename=Permission.SAMPLE_DELETE)

        # Create role
        self.role = Role.objects.create(name=Role.LAB_TECHNICIAN)

        # Create user
        self.user = User.objects.create_user(
            username="jane.doe",
            email="jane@lab.local",
            password="password123",
            tenant=self.tenant,
            role=self.role,
        )

    def test_user_has_permission_true(self):
        """User with permission returns True."""
        from core.models import RolePermission

        perm = Permission.objects.get(codename=Permission.SAMPLE_VIEW)
        RolePermission.objects.create(role=self.role, permission=perm)

        self.assertTrue(self.user.has_permission(Permission.SAMPLE_VIEW))

    def test_user_has_permission_false(self):
        """User without permission returns False."""
        self.assertFalse(self.user.has_permission(Permission.SAMPLE_DELETE))

    def test_inactive_user_has_no_permissions(self):
        """Inactive user returns False for all permissions."""
        from core.models import RolePermission

        perm = Permission.objects.get(codename=Permission.SAMPLE_VIEW)
        RolePermission.objects.create(role=self.role, permission=perm)

        # Deactivate user
        self.user.is_active = False
        self.user.save()

        self.assertFalse(self.user.has_permission(Permission.SAMPLE_VIEW))

    def test_user_without_role_has_no_permissions(self):
        """User without role returns False for all permissions."""
        self.user.role = None
        self.user.save()

        self.assertFalse(self.user.has_permission(Permission.SAMPLE_VIEW))
