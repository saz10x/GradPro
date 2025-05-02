# training/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
import json
import random
from .models import Scenario, Question, Answer, Response, UserScenarioResult, StoredScenario
from pages.models import AttackType
from .ai_utils import generate_scenario, parse_ai_response_json


def training_home(request):
    if not request.user.is_authenticated:
        return redirect('/users/login/')
    return render(request, 'training/training_home.html')


def training_login(request):
    return render(request, 'training/login.html')


@login_required
def select_attack(request):
    """عرض صفحة اختيار نوع الهجوم"""
    return render(request, 'training/select_attack.html')


@login_required
def scenario_view(request, attack_type):
    """
    عرض سيناريو تدريبي محدد بناءً على نوع الهجوم المختار.
    يحاول أولاً توليد سيناريو جديد بالذكاء الاصطناعي، وإذا فشل يستخدم سيناريو مخزن.
    
    Args:
        request: كائن HttpRequest
        attack_type: نوع الهجوم (ransomware, ddos, mitm)
    
    Returns:
        HttpResponse: استجابة تتضمن صفحة السيناريو
    """
    # التحقق من أن نوع الهجوم صالح
    valid_types = ['ransomware', 'ddos', 'mitm']
    if attack_type.lower() not in valid_types:
        messages.error(request, 'Invalid attack type')
        return redirect('training:select_attack')
    
    # الحصول على نوع الهجوم من قاعدة البيانات
    try:
        attack_type_obj = AttackType.objects.get(name__iexact=attack_type.lower())
    except AttackType.DoesNotExist:
        # إنشاء نوع هجوم جديد إذا لم يكن موجودًا
        attack_type_obj = AttackType.objects.create(
            name=attack_type.lower(),
            description=f"Description for {attack_type}",
            icon=f"bi-shield-{attack_type.lower()}"
        )
    
    # خطوة 1: محاولة توليد سيناريو جديد باستخدام الذكاء الاصطناعي
    try:
        # توليد سيناريو جديد باستخدام الذكاء الاصطناعي
        print(f"Attempting to generate a new AI scenario for {attack_type}")
        json_data = generate_scenario(attack_type.lower())
        
        # التحقق من صحة البيانات المولدة
        if not json_data or 'scenario' not in json_data or 'questions' not in json_data:
            print("Invalid AI response format, trying stored scenarios")
            raise Exception("Invalid AI response format")
            
        # استخراج نص السيناريو والتفاصيل المحددة
        scenario_text = json_data.get('scenario', {}).get('scenarioText', '')
        
        # هنا نتحقق من أن السيناريو ليس السيناريو الافتراضي
        if "TechVision Inc" in scenario_text and attack_type.lower() == 'ransomware':
            print("Default ransomware scenario detected, trying to generate a new one")
            raise Exception("Default scenario detected")
            
        if "GlobalStream" in scenario_text and attack_type.lower() == 'ddos':
            print("Default DDoS scenario detected, trying to generate a new one")
            raise Exception("Default scenario detected")
            
        if "FinSecure" in scenario_text and attack_type.lower() == 'mitm':
            print("Default MitM scenario detected, trying to generate a new one")
            raise Exception("Default scenario detected")
            
        # حفظ السيناريو المولد في قاعدة البيانات لاستخدامه لاحقاً
        new_stored_scenario = StoredScenario.objects.create(
            attack_type=attack_type_obj,
            title=f"AI-Generated {attack_type.capitalize()} Scenario ({timezone.now().strftime('%Y-%m-%d %H:%M')})",
            json_data=json_data
        )
        print(f"Successfully generated and stored new AI scenario with ID {new_stored_scenario.id}")
        
    except Exception as e:
        # إذا فشل توليد السيناريو، استخدم سيناريو مخزن
        print(f"Error generating scenario: {str(e)}")
        
        # خطوة 2: البحث عن سيناريو مخزن في قاعدة البيانات
        stored_scenarios = StoredScenario.objects.filter(attack_type=attack_type_obj)
        
        if stored_scenarios.exists():
            # اختيار سيناريو عشوائي من قاعدة البيانات
            stored_scenario = random.choice(stored_scenarios)
            json_data = stored_scenario.json_data
            print(f"Using stored scenario: {stored_scenario.title}")
        else:
            # لا توجد سيناريوهات مخزنة، إنشاء سيناريو بسيط
            print("No stored scenarios found, creating a simple scenario")
            scenario_text = f"Could not generate scenario for {attack_type}. Please try again later."
            json_data = {
                'scenario': {
                    'scenarioText': scenario_text,
                    'attackType': attack_type,
                    'specificDetails': {}
                },
                'questions': [
                    {
                        'questionText': "What is the most important step in cybersecurity incident response?",
                        'options': [
                            "Report the incident to appropriate personnel",
                            "Panic and shut down all systems",
                            "Try to fix the issue without telling anyone",
                            "Ignore the incident if it seems minor"
                        ],
                        'correctAnswerIndex': 0,
                        'explanation': "Always report security incidents to the appropriate personnel or team."
                    }
                ]
            }
    
    # خطوة 3: إنشاء كائن سيناريو في قاعدة البيانات للمستخدم الحالي
    with transaction.atomic():
        # إنشاء سيناريو جديد للمستخدم
        scenario_text = json_data.get('scenario', {}).get('scenarioText', '')
        new_scenario = Scenario.objects.create(
            user=request.user,
            attack_type=attack_type_obj,
            scenario_text=scenario_text,
            json_data=json_data  # تخزين البيانات المنظمة كاملة
        )
        
        # خطوة 4: إنشاء الأسئلة والإجابات في قاعدة البيانات
        questions_data = json_data.get('questions', [])
        for q_data in questions_data:
            # إنشاء سؤال
            question = Question.objects.create(
                scenario=new_scenario,
                question_text=q_data.get('questionText', ''),
                question_type='multiple_choice',
                explanation=q_data.get('explanation', '')
            )
            
            # إنشاء الخيارات والإجابات
            options = q_data.get('options', [])
            correct_index = q_data.get('correctAnswerIndex', 0)
            
            for i, option_text in enumerate(options):
                Answer.objects.create(
                    question=question,
                    answer_text=option_text,
                    is_correct=(i == correct_index)
                )
    
    # خطوة 5: عرض السيناريو والأسئلة للمستخدم
    questions = Question.objects.filter(scenario=new_scenario).prefetch_related('answers')
    
    context = {
        'scenario': new_scenario,
        'questions': questions,
        'attack_type': attack_type
    }
    
    return render(request, 'training/scenario.html', context)


@login_required
def scenario(request, scenario_id):
    """عرض سيناريو محدد بناءً على معرفه"""
    scenario = get_object_or_404(Scenario, scenario_id=scenario_id)
    questions = Question.objects.filter(scenario=scenario).prefetch_related('answers')
    
    context = {
        'scenario': scenario,
        'questions': questions,
        'attack_type': scenario.attack_type.name,
        'scenario_id': scenario_id
    }
    
    return render(request, 'training/scenario.html', context)


@login_required
def submit_answers(request, attack_type):
    """معالجة إجابات المستخدم وعرض التغذية الراجعة"""
    if request.method != 'POST':
        return redirect('training:select_attack')
    
    # الحصول على آخر سيناريو للمستخدم من هذا النوع
    attack_type_obj = get_object_or_404(AttackType, name__iexact=attack_type.lower())
    
    # البحث عن أحدث سيناريو للمستخدم من هذا النوع
    try:
        scenario = Scenario.objects.filter(
            user=request.user,
            attack_type=attack_type_obj
        ).latest('created_at')
    except Scenario.DoesNotExist:
        messages.error(request, 'Scenario not found')
        return redirect('training:select_attack')
    
    # الحصول على الأسئلة
    questions = Question.objects.filter(scenario=scenario).prefetch_related('answers')
    total_questions = questions.count()
    
    if total_questions == 0:
        messages.error(request, 'No questions found for this scenario')
        return redirect('training:select_attack')
    
    # معالجة الإجابات
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
        result = UserScenarioResult.objects.create(
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
        'score': percentage,  # إرسال النسبة المئوية بدلاً من عدد الإجابات الصحيحة
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'percentage': percentage,
        'feedback': feedback,
        'scenario_id': scenario.scenario_id
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
    
    # الحصول على الإجابات المقدمة للحصول على تفاصيل حول ما تم الإجابة عليه بشكل صحيح أو خاطئ
    responses = Response.objects.filter(
        user=request.user,
        scenario=scenario
    ).select_related('answer', 'answer__question')
    
    # الحصول على الأسئلة والإجابات الصحيحة
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
        'score': user_result.percentage,  # إرسال النسبة المئوية بدلاً من عدد الإجابات الصحيحة
        'correct_answers': user_result.score,
        'total_questions': user_result.total_questions,
        'percentage': user_result.percentage,
        'feedback': user_result.feedback,
        'question_data': question_data,
        'scenario_id': scenario_id,
        'attack_type': scenario.attack_type.name
    }
    
    return render(request, 'training/feedback.html', context)