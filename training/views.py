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
from .ai_utils import generate_scenario, parse_ai_response_json, init_genai
import google.generativeai as genai
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa


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


def generate_ai_feedback(scenario, correct_answers, total_questions, percentage, user_responses):
    """
    توليد تغذية راجعة مخصصة باستخدام الذكاء الاصطناعي
    
    Args:
        scenario: كائن السيناريو
        correct_answers: عدد الإجابات الصحيحة
        total_questions: إجمالي عدد الأسئلة
        percentage: النسبة المئوية للإجابات الصحيحة
        user_responses: قاموس يحتوي على إجابات المستخدم وتفاصيلها
    
    Returns:
        str: نص التغذية الراجعة المولدة
    """
    # تهيئة API
    init_genai()
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # إعداد معلومات السيناريو للبرومت
        scenario_info = f"Attack type: {scenario.attack_type.name.upper()}\n"
        
        if scenario.json_data and 'scenario' in scenario.json_data:
            # استخراج تفاصيل السيناريو المخزنة في JSON
            specific_details = scenario.json_data.get('scenario', {}).get('specificDetails', {})
            if specific_details:
                scenario_info += "Scenario details:\n"
                for key, value in specific_details.items():
                    scenario_info += f"- {key}: {value}\n"
        
        # إعداد معلومات إجابات المستخدم
        user_answer_info = "User's answers:\n"
        for q_id, details in user_responses.items():
            is_correct = "✓" if details['is_correct'] else "✗"
            user_answer_info += f"Q: {details['question_text']}\n"
            user_answer_info += f"User answered: {details['selected_answer']} {is_correct}\n"
            user_answer_info += f"Correct answer: {details['correct_answer']}\n\n"
        
        # بناء البرومت الكامل
        prompt = f"""
        Generate a personalized, educational feedback for a cybersecurity training scenario.
        
        {scenario_info}
        
        Performance summary:
        - Correct answers: {correct_answers} out of {total_questions}
        - Score: {percentage:.1f}%
        
        {user_answer_info}
        
        Please generate personalized feedback that:
        1. Gives an overall assessment of the trainee's understanding
        2. Identifies 3-4 specific strengths or areas for improvement based on their answers
        3. Provides practical recommendations for further learning
        4. Is encouraging, educational, and professional in tone
        5.don't write "Okay, here's personalized feedback based on your performance in the ransomware scenario." start the feedback example with "Excellent work!" if high score or "Good job!" if medium score or "Thank you for completing this cybersecurity training scenario." if low score.
        6. remove all **  or #  don't use any markdown formatting in the feedback.

        Format your response in 3-4 paragraphs with numbers points for key recommendations.
        """
        
        # إرسال البرومت إلى الذكاء الاصطناعي
        response = model.generate_content(prompt)
        
        # التحقق من الاستجابة   
        if response and hasattr(response, 'text') and response.text:
            ai_feedback = response.text.strip()
            # التحقق من جودة التغذية الراجعة
            if len(ai_feedback) > 100:
                return ai_feedback
        
        # إذا وصلنا إلى هنا، فشلت محاولة توليد تغذية راجعة مناسبة
        print("Generated feedback is too short or empty, using fallback")
        
    except Exception as e:
        print(f"Error generating AI feedback: {str(e)}")
    
    # استخدام تغذية راجعة بسيطة كخطة بديلة
    if percentage >= 80:
        return """
        Excellent work! You have demonstrated a strong understanding of the key concepts and security principles related to this cybersecurity scenario.
        
        Your strengths:
        • You correctly identified the attack vectors and initial entry points
        • You showed good knowledge of proper incident response procedures
        • You understand the technical aspects of the attack methodology
        
        Recommendations for further improvement:
        • Continue to practice with more complex scenarios to refine your skills
        • Consider exploring advanced training in threat hunting and analysis
        • Review the latest developments in protection mechanisms against this type of attack
        
        Keep up the great work! Your strong performance indicates you are well-equipped to handle similar security situations in a real-world environment.
        """
    elif percentage >= 60:
        return """
        Good job! You have a solid foundation in understanding this cybersecurity scenario, though there are areas you can improve.
        
        Your strengths:
        • You correctly identified the basic attack patterns
        • You understand fundamental security principles
        • You recognized several key warning signs of the attack
        
        Areas for improvement:
        • Pay closer attention to the technical details of attack vectors
        • Review incident response procedures, particularly the initial containment steps
        • Focus on understanding the organizational vulnerabilities that enabled the attack
        
        Recommendation: Consider reviewing best practices for this type of security incident and practice with additional scenarios to reinforce your knowledge. With more practice, you will be able to identify and respond to these threats more effectively.
        """
    else:
        return """
        Thank you for completing this cybersecurity training scenario. This was a challenging exercise, and it identifies several areas where further study would be beneficial.
        
        Key observations:
        • You were able to identify some aspects of the security incident
        • There are significant gaps in understanding the attack methodology and appropriate responses
        • More familiarity with security protocols would help improve your performance
        
        Recommendations for improvement:
        • Review the fundamentals of this type of cyber attack, focusing on initial indicators
        • Study proper incident response procedures and containment strategies
        • Practice identifying warning signs and attack patterns in similar scenarios
        • Consider taking an introductory course on cybersecurity principles
        
        Don't be discouraged! Security expertise comes with practice and continued learning. We recommend revisiting this scenario after reviewing the suggested materials to strengthen your knowledge in this area.
        """


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
    user_responses = {}  # لتخزين إجابات المستخدم بتنسيق مناسب للذكاء الاصطناعي
    
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
            
            # إعداد البيانات لتوليد التغذية الراجعة
            correct_answer = question.answers.filter(is_correct=True).first()
            user_responses[question.question_id] = {
                'question_text': question.question_text,
                'selected_answer': selected_answer.answer_text,
                'correct_answer': correct_answer.answer_text if correct_answer else "Unknown",
                'is_correct': is_correct,
                'explanation': question.explanation
            }
        
        # حساب النتيجة النهائية
        percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # توليد تغذية راجعة باستخدام الذكاء الاصطناعي
        ai_feedback = generate_ai_feedback(
            scenario=scenario,
            correct_answers=correct_answers,
            total_questions=total_questions,
            percentage=percentage,
            user_responses=user_responses
        )
        
        # حفظ نتيجة المستخدم مع التغذية الراجعة المخصصة
        result = UserScenarioResult.objects.create(
            user=request.user,
            scenario=scenario,
            score=correct_answers,
            total_questions=total_questions,
            percentage=percentage,
            feedback=ai_feedback
        )
    
    # إعداد سياق النتائج
    context = {
        'scenario': scenario,
        'score': percentage,  # إرسال النسبة المئوية بدلاً من عدد الإجابات الصحيحة
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'percentage': percentage,
        'feedback': ai_feedback,
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



def download_feedback_pdf(request, scenario_id):
    """
    إنشاء وتنزيل التغذية الراجعة كملف PDF
    """
    scenario = get_object_or_404(Scenario, scenario_id=scenario_id)
    
    # التحقق من أن المستخدم هو صاحب السيناريو
    if scenario.user != request.user:
        messages.error(request, 'You do not have permission to access this feedback')
        return redirect('training:select_attack')
    
    # الحصول على نتيجة المستخدم
    user_result = UserScenarioResult.objects.filter(
        user=request.user,
        scenario=scenario
    ).order_by('-completed_at').first()
    
    if not user_result:
        messages.warning(request, 'No results found for this scenario')
        return redirect('training:select_attack')
    
    # الحصول على الإجابات المقدمة والأسئلة
    responses = Response.objects.filter(
        user=request.user,
        scenario=scenario
    ).select_related('answer', 'answer__question')
    
    questions = Question.objects.filter(scenario=scenario).prefetch_related('answers')
    
    # إعداد بيانات الأسئلة والإجابات
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
    
    # إعداد سياق البيانات للقالب
    context = {
        'scenario': scenario,
        'correct_answers': user_result.score,
        'total_questions': user_result.total_questions,
        'percentage': user_result.percentage,
        'feedback': user_result.feedback,
        'question_data': question_data,
        'date': timezone.now().strftime("%Y-%m-%d %H:%M"),
        'user': request.user,
    }
    
    # تحميل قالب HTML للتقرير
    template = get_template('training/pdf_feedback_template.html')
    html = template.render(context)
    
    # إنشاء استجابة PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f"feedback_{scenario.attack_type.name}_{timezone.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # إنشاء ملف PDF
    pdf_status = create_pdf(html, response)
    
    # التحقق من نجاح إنشاء PDF
    if not pdf_status:
        messages.error(request, 'Error generating PDF')
        return redirect('training:feedback', scenario_id=scenario_id)
    
    return response

def create_pdf(html, result):
    """مساعد لإنشاء PDF من HTML"""
    # إنشاء كائن PDF
    pisa_status = pisa.CreatePDF(
        html,                  # محتوى HTML للتحويل
        dest=result,           # وجهة التقرير (HttpResponse)
        encoding='UTF-8'       # الترميز
    )
    # إعادة حالة النجاح
    return not pisa_status.err