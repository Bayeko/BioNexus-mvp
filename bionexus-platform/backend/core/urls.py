from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('protocols/', include('modules.protocols.urls')),
    path('samples/', include('modules.samples.urls')),
]
