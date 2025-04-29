from django.contrib import admin
from .models import AttackType, ContactMessage

admin.site.register(AttackType)
admin.site.register(ContactMessage)

class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'contact_type', 'subject', 'created_at')
    list_filter = ('contact_type', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)

# Unregister models if they're already registered
try:
    admin.site.unregister(ContactMessage)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(AttackType)
except admin.sites.NotRegistered:
    pass

# Re-register models with our custom admin classes
admin.site.register(ContactMessage, ContactMessageAdmin)
admin.site.register(AttackType)