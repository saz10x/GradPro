from typing import Self
from django import forms
from .models import ContactMessage, AttackType




class CustomCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = 'widgets/custom_checkbox_select.html'
    option_template_name = 'widgets/custom_checkbox_option.html'

class ContactForm(forms.ModelForm):
    SUGGESTED_ATTACKS = [
        ('phishing', 'Phishing'),
        ('sql_injection', 'SQL Injection'),
        ('xss', 'Cross-Site Scripting (XSS)'),
        ('social_engineering', 'Social Engineering'),
        ('malware', 'Malware'),
        ('zero_day', 'Zero Day Exploits'),
        ('bruteforce', 'Brute Force Attacks'),
        ('insider_threat', 'Insider Threats'),
        
    ]
    
    attack_types = forms.MultipleChoiceField(
        choices=SUGGESTED_ATTACKS,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'attack-types-checkbox'}),
        label="Attack types you'd like to see added to the platform",
        
    )
    
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'contact_type', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email'}),
            'contact_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your Message', 'rows': 5}),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Save the selected attack types
        instance.requested_attacks = ', '.join(self.cleaned_data.get('attack_types', []))
        if commit:
            instance.save()
        return instance