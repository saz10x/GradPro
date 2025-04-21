from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import Scenario, Question, Answer, Response, UserScenarioResult
from pages.models import AttackType
from .ai_utils import generate_scenario

def training_home(request):
    if not request.user.is_authenticated:
        print("User not authenticated, redirecting to login")  # للتشخيص
        return redirect('/users/login/')  # استخدم المسار المطلق للتحقق
    return render(request, 'training/training_home.html')

def training_login(request):
    return render(request, 'training/login.html')

@login_required
def select_attack(request):
    """عرض صفحة اختيار نوع الهجوم"""
    return render(request, 'training/select_attack.html')

@login_required
def scenario_view(request, attack_type):
    """عرض سيناريو تدريبي محدد بناءً على نوع الهجوم المختار"""
    # التحقق من أن نوع الهجوم صالح
    valid_types = ['ransomware', 'ddos', 'mitm']
    if attack_type not in valid_types:
        return redirect('training:select_attack')
    
    # الحصول على نوع الهجوم من قاعدة البيانات
    try:
        attack_type_obj = AttackType.objects.get(name=attack_type.lower())
    except AttackType.DoesNotExist:
        messages.error(request, 'Invalid attack type')
        return redirect('training:select_attack')
    

    # إنشاء سيناريو جديد مباشرة
    ai_response = generate_scenario(attack_type.lower())
    
    if not ai_response:
        # إذا فشل إنشاء سيناريو بالذكاء الاصطناعي، قم بإنشاء سيناريو بسيط للاختبار
        scenario_text = f"This is a sample {attack_type} scenario for testing."
        ai_response = {
            'scenario': {
                'scenarioText': scenario_text,
                'specificDetails': {
                    'initialInfectionVector': 'Email attachment',
                    'ransomAmount': '5000',
                    'deadline': '2023-01-01 00:00:00',
                    'typeVector': 'WiFi spoofing',
                    'dataIntercepted': 'User credentials',
                    'typeOfDDoS': 'SYN flood',
                    'attackVector': 'Botnet',
                    'targetedService': 'Web server',
                    'duration': '2 hours'
                }
            },
            'questions': [
                {
                    'questionText': f'What is the most common initial vector for a {attack_type} attack?',
                    'options': [
                        'Email attachment',
                        'USB drive',
                        'Remote desktop',
                        'Public WiFi'
                    ],
                    'correctAnswerIndex': 0,
                    'explanation': 'Email attachments are commonly used as initial infection vectors.'
                },
                {
                    'questionText': f'Which is the best defense against {attack_type} attacks?',
                    'options': [
                        'Firewalls only',
                        'Regular backups and security awareness',
                        'Antivirus only',
                        'Disable all external connections'
                    ],
                    'correctAnswerIndex': 1,
                    'explanation': 'A multi-layered approach with backups and awareness is most effective.'
                }
            ]
        }
    
    # إنشاء سيناريو جديد
    with transaction.atomic():
        # إنشاء السيناريو الأساسي
        scenario_text = ai_response.get('scenario', {}).get('scenarioText', '')
        new_scenario = Scenario.objects.create(
            user=request.user,
            attack_type=attack_type_obj,
            scenario_text=scenario_text,
            ai_response=ai_response,
            raw_response=str(ai_response)
        )
        
        # إنشاء التفاصيل الخاصة بنوع الهجوم
        specific_details = ai_response.get('scenario', {}).get('specificDetails', {})
        
        if attack_type.lower() == 'ransomware':
            from .models import RansomwareScenario
            
            # تحويل قيمة الفدية إلى قيمة عددية
            try:
                ransom_amount = float(specific_details.get('ransomAmount', '0').replace('$', '').replace(',', ''))
            except (ValueError, TypeError):
                ransom_amount = 5000.0  # قيمة افتراضية
                
            RansomwareScenario.objects.create(
                scenario=new_scenario,
                initial_infection_vector=specific_details.get('initialInfectionVector', ''),
                ransom_amount=ransom_amount,
                ransom_amount_text=specific_details.get('ransomAmount', ''),
                deadline=specific_details.get('deadline', None) or "2023-01-01 00:00:00"
            )
        elif attack_type.lower() == 'mitm':
            from .models import MitMScenario
            MitMScenario.objects.create(
                scenario=new_scenario,
                type_vector=specific_details.get('typeVector', ''),
                data_intercepted=specific_details.get('dataIntercepted', '')
            )
        elif attack_type.lower() == 'ddos':
            from .models import DDoSScenario
            DDoSScenario.objects.create(
                scenario=new_scenario,
                type_of_ddos=specific_details.get('typeOfDDoS', ''),
                attack_vector=specific_details.get('attackVector', ''),
                targeted_service=specific_details.get('targetedService', ''),
                duration=specific_details.get('duration', '')
            )
        
        # إنشاء الأسئلة والإجابات
        for q_data in ai_response.get('questions', []):
            question = Question.objects.create(
                scenario=new_scenario,
                question_text=q_data.get('questionText', ''),
                question_type='multiple_choice',
                explanation=q_data.get('explanation', '')
            )
            
            # إنشاء الخيارات
            for i, opt_text in enumerate(q_data.get('options', [])):
                Answer.objects.create(
                    question=question,
                    answer_text=opt_text,
                    is_correct=(i == q_data.get('correctAnswerIndex', 0))
                )
    
    # الحصول على الأسئلة والإجابات للعرض
    questions = Question.objects.filter(scenario=new_scenario).prefetch_related('answers')
    
    context = {
        'scenario': new_scenario,
        'questions': questions,
        'attack_type': attack_type
    }
    
    return render(request, 'training/scenario.html', context)
def get_random_existing_scenario(attack_type):
    """
    استرجاع سيناريو عشوائي من نفس النوع من قاعدة البيانات
    """
    try:
        attack_type_obj = AttackType.objects.get(name__iexact=attack_type.lower())
        # البحث عن سيناريوهات من نفس النوع
        existing_scenarios = Scenario.objects.filter(
            attack_type=attack_type_obj,
            # التأكد من أن السيناريو ليس فارغًا وليس سيناريو افتراضي للاختبار
            scenario_text__isnull=False,
        ).exclude(
            scenario_text__icontains="sample scenario for testing"
        )
        
        if existing_scenarios.exists():
            # اختيار سيناريو عشوائي
            import random
            return random.choice(existing_scenarios)
    except Exception as e:
        print(f"Error retrieving random scenario: {str(e)}")
    
    return None
@login_required
def scenario(request, scenario_id):
    """عرض سيناريو محدد بناءً على معرفه"""
    scenario = get_object_or_404(Scenario, scenario_id=scenario_id)
    questions = Question.objects.filter(scenario=scenario).prefetch_related('answers')
    
    context = {
        'scenario': scenario,
        'questions': questions,
        'attack_type': scenario.attack_type.name,
        'scenario_id': scenario_id  # Keep the original parameter to maintain compatibility
    }
    
    return render(request, 'training/scenario.html', context)

@login_required
def submit_answers(request, attack_type):
    """معالجة إجابات المستخدم وعرض التغذية الراجعة"""
    if request.method != 'POST':
        return redirect('training:select_attack')
    
    # الحصول على نوع الهجوم والسيناريو
    attack_type_obj = get_object_or_404(AttackType, name=attack_type.lower())
    scenario = get_object_or_404(Scenario, attack_type=attack_type_obj)
    
    # الحصول على الأسئلة
    questions = Question.objects.filter(scenario=scenario).prefetch_related('answers')
    
    # معالجة الإجابات
    score = 0
    total_questions = questions.count()
    correct_answers = 0
    
    with transaction.atomic():
        # مسح الإجابات السابقة لهذا المستخدم ولهذا السيناريو إذا وجدت
        Response.objects.filter(user=request.user, scenario=scenario).delete()
        
        for question in questions:
            # الحصول على الخيار المحدد
            answer_id = request.POST.get(f'question_{question.question_id}')
            if not answer_id:
                continue
            
            selected_answer = get_object_or_404(Answer, answer_id=answer_id, question=question)
            
            # تحديد ما إذا كانت الإجابة صحيحة
            is_correct = selected_answer.is_correct
            if is_correct:
                correct_answers += 1
            
            # حفظ إجابة المستخدم
            Response.objects.create(
                user=request.user,
                scenario=scenario,
                answer=selected_answer,
                submitted_at=timezone.now()
            )
        
        # حساب النتيجة النهائية
        percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # توليد تغذية راجعة بسيطة
        if percentage >= 80:
            feedback = "Excellent! You have a strong understanding of this type of attack."
        elif percentage >= 60:
            feedback = "Good job! You understand the basics, but there's room for improvement."
        else:
            feedback = "Try again. You might want to review the fundamentals of this type of attack."
        
        # حفظ نتيجة المستخدم
        UserScenarioResult.objects.create(
            user=request.user,
            scenario=scenario,
            score=correct_answers,
            total_questions=total_questions,
            percentage=percentage,
            feedback=feedback
        )
    
    # إعداد سياق النتائج
    context = {
        'scenario': scenario,
        'score': correct_answers,
        'total_questions': total_questions,
        'percentage': percentage,
        'feedback': feedback,
        'scenario_id': scenario.scenario_id  # Keep for backward compatibility
    }
    
    return render(request, 'training/feedback.html', context)

@login_required
def feedback(request, scenario_id):
    """عرض التغذية الراجعة لسيناريو محدد"""
    scenario = get_object_or_404(Scenario, scenario_id=scenario_id)
    
    # الحصول على آخر نتيجة للمستخدم لهذا السيناريو
    user_result = UserScenarioResult.objects.filter(
        user=request.user,
        scenario=scenario
    ).order_by('-completed_at').first()
    
    if not user_result:
        messages.warning(request, 'No results found for this scenario')
        return redirect('training:scenario', scenario_id=scenario_id)
    
    # احصل على الإجابات المقدمة للحصول على تفاصيل حول ما تم الإجابة عليه بشكل صحيح أو خاطئ
    responses = Response.objects.filter(
        user=request.user,
        scenario=scenario
    ).select_related('answer', 'answer__question')
    
    # احصل على الأسئلة والإجابات الصحيحة
    questions = Question.objects.filter(scenario=scenario).prefetch_related('answers')
    
    # إنشاء قاموس للإجابات الصحيحة والإجابات المختارة
    question_data = {}
    for question in questions:
        correct_answer = question.answers.filter(is_correct=True).first()
        selected_response = next((r for r in responses if r.answer.question_id == question.question_id), None)
        
        question_data[question.question_id] = {
            'question_text': question.question_text,
            'correct_answer': correct_answer.answer_text if correct_answer else "Unknown",
            'selected_answer': selected_response.answer.answer_text if selected_response else "Not answered",
            'is_correct': selected_response and selected_response.answer.is_correct if selected_response else False,
            'explanation': question.explanation
        }
    
    context = {
        'scenario': scenario,
        'score': user_result.score,
        'total_questions': user_result.total_questions,
        'percentage': user_result.percentage,
        'feedback': user_result.feedback,
        'question_data': question_data,
        'scenario_id': scenario_id,  # Keep the original parameter
        'attack_type': scenario.attack_type.name
    }
    
    return render(request, 'training/feedback.html', context)