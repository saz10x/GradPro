import re
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cyber_security_platform2.settings')
django.setup()

from training.models import Scenario, Question, Answer, AttackType
from pages.models import AttackType
from django.contrib.auth.models import User

def clean_scenario_data():
    # الحصول على جميع السيناريوهات
    scenarios = Scenario.objects.all()
    
    for scenario in scenarios:
        scenario_text = scenario.scenario_text
        
        # فصل نص السيناريو عن الأسئلة
        if "##" in scenario_text:
            parts = scenario_text.split("##")
            clean_scenario_text = parts[0].strip()
            questions_text = parts[1].strip()
            
            # تحديث نص السيناريو ليحتوي على الوصف فقط
            scenario.scenario_text = clean_scenario_text
            scenario.save()
            
            # معالجة الأسئلة
            question_blocks = re.split(r'\*\*\d+\.', questions_text)
            question_blocks = [q for q in question_blocks if q.strip()]
            
            # استخراج أرقام الأسئلة
            question_numbers = re.findall(r'\*\*(\d+)\.', questions_text)
            
            # حذف الأسئلة والإجابات القديمة للسيناريو
            Question.objects.filter(scenario=scenario).delete()
            
            # إنشاء أسئلة وإجابات جديدة
            for i, block in enumerate(question_blocks):
                if i < len(question_numbers):
                    # استخراج نص السؤال
                    q_match = re.search(r'(.*?)\*\*', block)
                    if q_match:
                        question_text = q_match.group(1).strip()
                        
                        # إنشاء سؤال جديد
                        question = Question.objects.create(
                            scenario=scenario,
                            question_text=question_text,
                            question_type='multiple_choice'
                        )
                        
                        # استخراج الخيارات
                        options = re.findall(r'([a-d]\) .*?)(?=[a-d]\)|$|\*\*Correct Answer)', block)
                        correct_match = re.search(r'\*\*Correct Answer:\*\* ([a-d]\))', block)
                        
                        if correct_match:
                            correct_option = correct_match.group(1)[0]  # a, b, c, or d
                        else:
                            correct_option = 'a'  # افتراضي
                        
                        # إنشاء إجابات
                        for opt in options:
                            opt = opt.strip()
                            if opt:
                                option_letter = opt[0]
                                answer_text = opt[2:].strip()
                                
                                Answer.objects.create(
                                    question=question,
                                    answer_text=answer_text,
                                    is_correct=(option_letter == correct_option)
                                )
                        
                        print(f"Created question {question.question_id} with {len(options)} options")

if __name__ == "__main__":
    clean_scenario_data()
    print("Data cleaning complete!")