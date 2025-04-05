from django.contrib import admin
from .models import (
    Scenario, 
    RansomwareScenario, 
    MitMScenario, 
    DDoSScenario, 
    Question, 
    Answer, 
    Response,
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