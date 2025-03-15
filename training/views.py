from django.shortcuts import render , redirect
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect

def training_home(request):
    if not request.user.is_authenticated:
        print("User not authenticated, redirecting to login")  # للتشخيص
        return redirect('/users/login/')  # استخدم المسار المطلق للتحقق
    return render(request, 'training/training_home.html')

def training_login(request):
    return render(request, 'training/login.html')

def select_attack(request):
    return render(request, 'training/select_attack.html')

def scenario(request, scenario_id):
    return render(request, 'training/scenario.html', {'scenario_id': scenario_id})

def feedback(request, scenario_id):
    return render(request, 'training/feedback.html', {'scenario_id': scenario_id})