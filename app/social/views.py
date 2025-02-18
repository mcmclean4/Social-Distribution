from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
from django.http import HttpResponse

def stream(request):
    return HttpResponse("This is the stream.")