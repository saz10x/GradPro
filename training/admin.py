from django.contrib import admin
from .models import StoredScenario
from .models import (
    Scenario, 
    RansomwareScenario, 
    MitMScenario, 
    DDoSScenario, 
    Question, 
    Answer, 
    Response,
    StoredScenario,
)

# تسجيل النماذج الأساسية
admin.site.register(Scenario)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Response)

# تسجيل نماذج السيناريوهات المتخصصة
admin.site.register(RansomwareScenario)
admin.site.register(MitMScenario)
admin.site.register(DDoSScenario)



class StoredScenarioAdmin(admin.ModelAdmin):
    list_display = ['title', 'attack_type', 'created_at']
    list_filter = ['attack_type']
    search_fields = ['title']

admin.site.register(StoredScenario, StoredScenarioAdmin)