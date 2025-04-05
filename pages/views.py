from django.shortcuts import render, redirect
from django.contrib.auth import logout
from .models import AttackType
from .forms import ContactForm

def home(request):
    return render(request, 'pages/home.html')

def about(request):
    return render(request, 'pages/about.html')

def learn(request):
    attack_types = AttackType.objects.all()
    return render(request, 'pages/learn.html', {'attack_types': attack_types})

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('contact')
    else:
        form = ContactForm()
    
    return render(request, 'pages/contact.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')