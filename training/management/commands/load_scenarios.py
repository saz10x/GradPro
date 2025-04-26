from django.core.management.base import BaseCommand
from pages.models import AttackType
from training.models import StoredScenario
from training.ai_utils import create_default_scenario

class Command(BaseCommand):
    help = 'Load default scenarios into the database'

    def handle(self, *args, **kwargs):
        attack_types = ['ransomware', 'ddos', 'mitm']
        
        for attack_type in attack_types:
            # التأكد من وجود نوع الهجوم
            attack_type_obj, created = AttackType.objects.get_or_create(
                name=attack_type,
                defaults={'description': f'Description for {attack_type}'}
            )
            
            # إنشاء 5 سيناريوهات لكل نوع هجوم
            for i in range(5):
                # استخدام دالة إنشاء السيناريو الافتراضي
                scenario_data = create_default_scenario(attack_type)
                
                # تنظيم البيانات بصيغة JSON
                json_data = {
                    'scenario': {
                        'scenarioText': scenario_data['scenario']['scenarioText'],
                        'specificDetails': scenario_data['scenario']['specificDetails']
                    },
                    'questions': scenario_data['questions']
                }
                
                # تخزين السيناريو في قاعدة البيانات
                StoredScenario.objects.create(
                    attack_type=attack_type_obj,
                    title=f"{attack_type.capitalize()} Scenario {i+1}",
                    json_data=json_data
                )
                
                self.stdout.write(self.style.SUCCESS(f'Created {attack_type} scenario {i+1}'))