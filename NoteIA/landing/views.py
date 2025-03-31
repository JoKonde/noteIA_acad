from django.shortcuts import render

from django.shortcuts import render

def index(request):
    return render(request, 'landing/index.html')

def login(request):
    return render(request, 'landing/login.html')

def signup(request):
    return render(request, 'landing/signup.html')


def dashboard(request):
    return render(request, 'landing/dashboard.html')


def custom_404(request, exception):
    return render(request, 'landing/404.html', status=404)

def custom_500(request):
    return render(request, 'landing/500.html', status=500)

