# training/admin.py
from django.contrib import admin
from .models import (
    Scenario, 
    Question, 
    Answer, 
    Response,
    StoredScenario,
    UserScenarioResult
)

# تسجيل النماذج الأساسية
admin.site.register(Scenario)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Response)
admin.site.register(UserScenarioResult)

# تخصيص عرض StoredScenario في لوحة الإدارة
class StoredScenarioAdmin(admin.ModelAdmin):
    list_display = ['title', 'attack_type', 'created_at']
    list_filter = ['attack_type']
    search_fields = ['title']

admin.site.register(StoredScenario, StoredScenarioAdmin)