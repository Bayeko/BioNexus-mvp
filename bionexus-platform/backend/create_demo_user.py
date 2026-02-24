"""Script to create demo user - called by RUN.bat"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from core.models import Tenant, User

tenant, _ = Tenant.objects.get_or_create(name='Demo Lab', slug='demo-lab')

user, created = User.objects.get_or_create(
    username='demo_user',
    defaults={'email': 'demo@lab.local', 'tenant': tenant}
)
user.set_password('DemoPassword123!')
user.tenant = tenant
user.save()

if created:
    print('  Demo user created: demo_user / DemoPassword123!')
else:
    print('  Demo user already exists.')
