#!/usr/bin/env python
"""Create demo tenant + user for BioNexus demos.

Usage:
    python create_demo_user.py

Creates:
    - Tenant: "BioNexus Demo Laboratory" (slug: demo-lab)
    - User: demo_user / DemoPassword123!
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from core.models import Tenant, User

# Create tenant
tenant, created = Tenant.objects.get_or_create(
    slug="demo-lab",
    defaults={
        "name": "BioNexus Demo Laboratory",
        "description": "Demo laboratory for BioNexus MVP presentations",
    },
)
if created:
    print(f"Tenant created: {tenant.name}")
else:
    print(f"Tenant already exists: {tenant.name}")

# Create user
try:
    user = User.objects.get(username="demo_user", tenant=tenant)
    print(f"User already exists: {user.username}")
except User.DoesNotExist:
    user = User.objects.create_user(
        username="demo_user",
        email="demo@bionexus.local",
        password="DemoPassword123!",
        tenant=tenant,
    )
    print(f"Demo user created: {user.username} / DemoPassword123!")

print("\nReady! You can now log in with:")
print("  Username: demo_user")
print("  Password: DemoPassword123!")
