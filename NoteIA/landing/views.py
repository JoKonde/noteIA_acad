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
