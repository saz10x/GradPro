from django.db import models

class AttackType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.name

class AttackInformation(models.Model):
    attack_type = models.ForeignKey(AttackType, on_delete=models.CASCADE, related_name='information')
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    def __str__(self):
        return f"{self.title} - {self.attack_type.name}"

class ContactMessage(models.Model):
    CONTACT_TYPES = [
        ('inquiry', 'Inquiry'),
        ('feedback', 'Feedback'),
        ('complaint', 'Complaint'),
        ('suggestion', 'Suggestion'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPES, default='inquiry')
    subject = models.CharField(max_length=200, default='')
    message = models.TextField()
    requested_attacks = models.TextField(blank=True, null=True, help_text="Attack types requested to be added")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_contact_type_display()} from {self.name} - {self.created_at.strftime('%Y-%m-%d')}"