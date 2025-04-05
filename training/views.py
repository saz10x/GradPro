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
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def scenario_view(request, attack_type):
    """عرض سيناريو تدريبي محدد بناءً على نوع الهجوم المختار"""
    # التحقق من أن نوع الهجوم صالح
    valid_types = ['ransomware', 'ddos', 'mitm']
    if attack_type not in valid_types:
        return redirect('training:select_attack')
    
    context = {
        'attack_type': attack_type,
    }
    
    return render(request, 'training/scenario.html', context)
    