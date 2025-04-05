from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')  
        password = request.POST.get('password')
        
        try:
            # البحث عن المستخدم بواسطة البريد الإلكتروني
            user = User.objects.get(email=email)
            # محاولة المصادقة باستخدام اسم المستخدم وكلمة المرور
            user = authenticate(request, username=user.username, password=password)
            
            if user is not None:
                login(request, user)
                # توجيه المستخدم إلى صفحة اختيار السيناريو بعد تسجيل الدخول
                return redirect('training:select_attack')
            else:
                messages.error(request, 'Invalid email or password')
        except User.DoesNotExist:
            messages.error(request, 'User with this email does not exist')
    
    return render(request, 'users/login.html')

def register_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')
        
        # التحقق من تطابق كلمات المرور
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'users/register.html')
        
        # التحقق من عدم وجود حساب بنفس البريد الإلكتروني
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email is already registered')
            return render(request, 'users/register.html')
        
        # إنشاء اسم مستخدم من البريد الإلكتروني
        username = email.split('@')[0]
        
        # التأكد من عدم تكرار اسم المستخدم
        i = 1
        temp_username = username
        while User.objects.filter(username=temp_username).exists():
            temp_username = f"{username}{i}"
            i += 1
        username = temp_username
        
        # إنشاء المستخدم الجديد
        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # تسجيل الدخول تلقائياً بعد إنشاء الحساب
        login(request, user)
        
        messages.success(request, 'Account created successfully.')
        # توجيه المستخدم إلى صفحة اختيار السيناريو بعد إنشاء الحساب
        return redirect('/training/select/')
    
    return render(request, 'users/register.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def profile_view(request):
    return render(request, 'users/profile.html')