# backend/core/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Incluez les URLs de vos modules
    path('compliance/', include('modules.compliance.urls')),
    path('customization/', include('modules.customization.urls')),
    # Ajoutez les autres modules ici
]
