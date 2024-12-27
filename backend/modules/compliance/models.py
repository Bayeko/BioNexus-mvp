# backend/modules/compliance/models.py

from django.db import models

class Compliance(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name
