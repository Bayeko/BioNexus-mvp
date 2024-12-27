from django.urls import path
from . import views

urlpatterns = [
    path('', views.compliance_home, name='compliance_home'),
    # Ajouter d'autres routes si nécessaire
]
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('compliance/', include('modules.compliance.urls')),
    path('customization/', include('modules.customization.urls')),
    path('equipments/', include('modules.equipments.urls')),
    path('i18n/', include('modules.i18n.urls')),
    path('reporting/', include('modules.reporting.urls')),
    path('userperm/', include('modules.userperm.urls')),
    path('api/', include('modules.samples.urls')),
    # Ajouter d'autres modules ici
]
