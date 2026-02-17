"""Shared test fixtures for authentication and multi-tenant isolation."""

from core.models import Tenant, Role, User, Permission, RolePermission


def create_test_tenant(name="Test Lab A", slug="test-lab-a"):
    """Create a test tenant."""
    return Tenant.objects.create(
        name=name,
        slug=slug,
        description="Test laboratory",
    )


def create_test_role(name=Role.LAB_TECHNICIAN):
    """Create a test role."""
    return Role.objects.get_or_create(name=name)[0]


def create_test_user(
    tenant=None,
    username="test_user",
    email="test@lab.local",
    password="testpass123",
    role=None
):
    """Create a test user."""
    if not tenant:
        tenant = create_test_tenant()
    if not role:
        role = create_test_role()

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        tenant=tenant,
        role=role,
    )
    return user


def create_test_permissions():
    """Create all standard permissions."""
    permissions = [
        Permission.SAMPLE_VIEW,
        Permission.SAMPLE_CREATE,
        Permission.SAMPLE_UPDATE,
        Permission.SAMPLE_DELETE,
        Permission.PROTOCOL_VIEW,
        Permission.PROTOCOL_CREATE,
        Permission.PROTOCOL_UPDATE,
        Permission.PROTOCOL_DELETE,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        Permission.USER_MANAGE,
        Permission.ROLE_MANAGE,
    ]

    return [
        Permission.objects.get_or_create(codename=perm)[0]
        for perm in permissions
    ]


def assign_permissions_to_role(role, permission_codenames):
    """Assign a list of permissions to a role."""
    for codename in permission_codenames:
        permission = Permission.objects.get(codename=codename)
        RolePermission.objects.get_or_create(role=role, permission=permission)
