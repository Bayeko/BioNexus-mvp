from django.shortcuts import render
from django.http import HttpResponse

def compliance_home(request):
    return HttpResponse("Bienvenue sur la page Compliance!")
