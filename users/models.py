from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = [
        ('IT_MANAGER', 'IT Manager'),
        ('SECURITY_ANALYST', 'Security Analyst'),
        ('EMPLOYEE', 'Employee'),
        ('IT_SPECIALIST', 'IT Specialist'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"