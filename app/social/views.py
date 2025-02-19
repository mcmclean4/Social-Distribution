from django.shortcuts import render

def stream(request):
    return render(request, 'social/index.html', {})

