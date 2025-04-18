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
    
    # البحث عن سيناريو موجود لهذا النوع من الهجمات
    existing_scenario = Scenario.objects.filter(
        attack_type=attack_type_obj
    ).order_by('-created_at').first()
    
    # إذا لم يكن هناك سيناريو، قم بإنشاء واحد جديد
    if not existing_scenario:
        # استدعاء Gemini API
        ai_response = generate_scenario(attack_type.lower())
        
        if not ai_response:
            messages.error(request, 'Error creating scenario. Please try again.')
            return redirect('training:select_attack')
        
        # إنشاء سيناريو جديد
        with transaction.atomic():
            # إنشاء السيناريو الأساسي
            scenario_text = ai_response.get('scenario', {}).get('scenarioText', '')
            existing_scenario = Scenario.objects.create(
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
                RansomwareScenario.objects.create(
                    scenario=existing_scenario,
                    initial_infection_vector=specific_details.get('initialInfectionVector', ''),
                    ransom_amount=specific_details.get('ransomAmount', 0),
                    deadline=specific_details.get('deadline', None) or "2023-01-01 00:00:00"
                )
            elif attack_type.lower() == 'mitm':
                from .models import MitMScenario
                MitMScenario.objects.create(
                    scenario=existing_scenario,
                    type_vector=specific_details.get('typeVector', ''),
                    data_intercepted=specific_details.get('dataIntercepted', '')
                )
            elif attack_type.lower() == 'ddos':
                from .models import DDoSScenario
                DDoSScenario.objects.create(
                    scenario=existing_scenario,
                    type_of_ddos=specific_details.get('typeOfDDoS', ''),
                    attack_vector=specific_details.get('attackVector', ''),
                    targeted_service=specific_details.get('targetedService', ''),
                    duration=specific_details.get('duration', '')
                )
            
            # إنشاء الأسئلة والإجابات
            for q_data in ai_response.get('questions', []):
                question = Question.objects.create(
                    scenario=existing_scenario,
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
    questions = Question.objects.filter(scenario=existing_scenario).prefetch_related('answers')
    
    context = {
        'scenario': existing_scenario,
        'questions': questions,
        'attack_type': attack_type
    }
    
    return render(request, 'training/scenario.html', context)

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
    
    with transaction.atomic():
        for question in questions:
            # الحصول على الخيار المحدد
            answer_id = request.POST.get(f'question_{question.question_id}')
            if not answer_id:
                continue
            
            selected_answer = get_object_or_404(Answer, answer_id=answer_id, question=question)
            
            # تحديد ما إذا كانت الإجابة صحيحة
            is_correct = selected_answer.is_correct
            if is_correct:
                score += 1
            
            # حفظ إجابة المستخدم
            Response.objects.create(
                user=request.user,
                scenario=scenario,
                answer=selected_answer,
                submitted_at=timezone.now()
            )
        
        # حساب النتيجة النهائية
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        
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
            score=score,
            total_questions=total_questions,
            percentage=percentage,
            feedback=feedback
        )
    
    # إعداد سياق النتائج
    context = {
        'scenario': scenario,
        'score': score,
        'total_questions': total_questions,
        'percentage': percentage,
        'feedback': feedback,
        'scenario_id': scenario.scenario_id  # Keep for backward compatibility
    }
    
    return render(request, 'training/feedback.html', context)

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
    
    context = {
        'scenario': scenario,
        'score': user_result.score,
        'total_questions': user_result.total_questions,
        'percentage': user_result.percentage,
        'feedback': user_result.feedback,
        'scenario_id': scenario_id  # Keep the original parameter
    }
    
    return render(request, 'training/feedback.html', context)