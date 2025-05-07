from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages  # استيراد صحيح من django.contrib
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
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
        else:
            # في حالة عدم صحة النموذج
            messages.error(request, 'There was an error with your submission. Please check the form.')
    else:
        form = ContactForm()
    
    return render(request, 'pages/contact.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')