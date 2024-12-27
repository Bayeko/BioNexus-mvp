# backend/modules/samples/views.py

from rest_framework import viewsets
from .models import Sample
from .serializers import SampleSerializer
from rest_framework.permissions import IsAuthenticated

class SampleViewSet(viewsets.ModelViewSet):
    queryset = Sample.objects.all()
    serializer_class = SampleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
