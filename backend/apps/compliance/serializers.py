from rest_framework import serializers
from .models import Compliance

class ComplianceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compliance
        fields = '__all__'
