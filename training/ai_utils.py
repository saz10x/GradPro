
import os
import json
import google.generativeai as genai
from django.conf import settings

# تهيئة API
def init_genai():
    genai.configure(api_key=settings.GEMINI_API_KEY)

def generate_scenario(attack_type):
    """
    توليد سيناريو تدريبي بناءً على نوع الهجوم
    """
    # تهيئة API
    init_genai()
    
    # تحديد نموذج Gemini
    model = genai.GenerativeModel("gemini-2.0-flash")

    
    prompt = f"""
    You are an expert in information security and cybersecurity. Create a realistic and comprehensive training scenario about a {attack_type} attack with 15 multiple-choice questions.
     
    ## Scenario Requirements:
    1. Provide a detailed, realistic, and comprehensive description of a {attack_type} attack in a real organizational environment
    2. The scenario must include details specific to the attack type:
    3. The scenario must be as a paragraph with 400 words or 500 words
     
       - If the attack is Ransomware:
         * Initial infection vector (InitialInfectionVector)
         * Ransom amount demanded (RansomAmount)
         * Payment deadline (Deadline)
     
       - If the attack is Man-in-the-Middle:
         * Type of attack vector (TypeVector)
         * Type of intercepted data (DataIntercepted)
     
       - If the attack is DDoS:
         * Type of DDoS attack (TypeOfDDoS)
         * Attack vector (AttackVector)
         * Targeted service (TargetedService)
         * Attack duration (Duration)
     
    ## Question Requirements:
    1. 15 multiple-choice questions directly related to the scenario
    2. Each question must have 4 potential options
    3. Only one correct answer per question
    4. Progressive difficulty level from basic to advanced
    5. Cover various aspects of the attack: detection, prevention, response, mitigation
    6. Include an explanation of why the chosen answer is correct
    
    Please respond with the scenario first, followed by all 15 questions with their options and correct answers.
    """
    
    try:
        # إرسال الطلب إلى Gemini API
        response = model.generate_content(prompt)
        
        # تحليل النص المستلم
        text_response = response.text
        
        # تحويل النص إلى تنسيق منظم
        scenario_data = parse_ai_response(text_response, attack_type)
        return scenario_data
            
    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        return None

def parse_ai_response(text_response, attack_type):
    """
    تحليل استجابة النص من الذكاء الاصطناعي وتحويلها إلى تنسيق منظم
    """
    # تقسيم النص إلى سيناريو وأسئلة
    lines = text_response.split('\n')
    
    # استخراج السيناريو (الفقرة الأولى عادة)
    scenario_text = ""
    question_section_start = False
    for line in lines:
        if line.strip().startswith("Question 1:") or line.strip().startswith("1."):
            question_section_start = True
            break
        if not question_section_start and line.strip():
            scenario_text += line + "\n"
    
    # استخراج خصائص السيناريو الإضافية
    specific_details = {}
    
    if attack_type.lower() == 'ransomware':
        # محاولة استخراج معلومات خاصة بالفدية
        if "infection vector" in text_response.lower():
            specific_details["initialInfectionVector"] = extract_detail(text_response, "infection vector")
        if "ransom" in text_response.lower() and "amount" in text_response.lower():
            specific_details["ransomAmount"] = extract_detail(text_response, "ransom amount")
        if "deadline" in text_response.lower():
            specific_details["deadline"] = extract_detail(text_response, "deadline")
            
    elif attack_type.lower() == 'mitm':
        # محاولة استخراج معلومات خاصة بهجمات الرجل في الوسط
        if "vector" in text_response.lower():
            specific_details["typeVector"] = extract_detail(text_response, "attack vector")
        if "intercept" in text_response.lower():
            specific_details["dataIntercepted"] = extract_detail(text_response, "data intercepted")
            
    elif attack_type.lower() == 'ddos':
        # محاولة استخراج معلومات خاصة بهجمات DDoS
        if "type of ddos" in text_response.lower():
            specific_details["typeOfDDoS"] = extract_detail(text_response, "type of ddos")
        if "vector" in text_response.lower():
            specific_details["attackVector"] = extract_detail(text_response, "attack vector")
        if "target" in text_response.lower():
            specific_details["targetedService"] = extract_detail(text_response, "targeted service")
        if "duration" in text_response.lower():
            specific_details["duration"] = extract_detail(text_response, "duration")
    
    # استخراج الأسئلة
    questions = []
    current_question = None
    
    for line in lines:
        line = line.strip()
        
        # التحقق من بداية سؤال جديد
        if line.startswith("Question") or (line and line[0].isdigit() and line[1] == '.'):
            if current_question:
                questions.append(current_question)
            
            current_question = {
                "questionText": line.split(":", 1)[1].strip() if ":" in line else line.split(".", 1)[1].strip(),
                "options": [],
                "correctAnswerIndex": None,
                "explanation": ""
            }
        
        # جمع الخيارات
        elif current_question and (line.startswith("A.") or line.startswith("B.") or 
                                   line.startswith("C.") or line.startswith("D.")):
            option_text = line[2:].strip()
            current_question["options"].append(option_text)
            
            # محاولة تحديد الإجابة الصحيحة
            if "correct" in line.lower() or "(correct)" in line.lower():
                if line.startswith("A."):
                    current_question["correctAnswerIndex"] = 0
                elif line.startswith("B."):
                    current_question["correctAnswerIndex"] = 1
                elif line.startswith("C."):
                    current_question["correctAnswerIndex"] = 2
                elif line.startswith("D."):
                    current_question["correctAnswerIndex"] = 3
        
        # جمع الشرح
        elif current_question and line.startswith("Correct answer:") or line.startswith("Explanation:"):
            current_question["explanation"] = line.split(":", 1)[1].strip()
            
            # تحديد الإجابة الصحيحة إذا لم تكن محددة بعد
            if current_question["correctAnswerIndex"] is None and line.startswith("Correct answer:"):
                if "A" in line:
                    current_question["correctAnswerIndex"] = 0
                elif "B" in line:
                    current_question["correctAnswerIndex"] = 1
                elif "C" in line:
                    current_question["correctAnswerIndex"] = 2
                elif "D" in line:
                    current_question["correctAnswerIndex"] = 3
    
    # إضافة السؤال الأخير
    if current_question:
        questions.append(current_question)
    
    # تنظيف البيانات وتصحيح أي أخطاء
    for q in questions:
        if q["correctAnswerIndex"] is None:
            q["correctAnswerIndex"] = 0  # تعيين الخيار الأول كإجابة افتراضية
    
    # تنسيق النتيجة النهائية
    return {
        "scenario": {
            "scenarioText": scenario_text.strip(),
            "attackType": attack_type,
            "specificDetails": specific_details
        },
        "questions": questions[:15]  # التأكد من وجود 15 سؤال فقط
    }

def extract_detail(text, keyword):
    """
    استخراج تفاصيل محددة من النص
    """
    # هذه دالة بسيطة لاستخراج معلومات من النص - يمكن تحسينها
    keyword = keyword.lower()
    lines = text.lower().split("\n")
    
    for i, line in enumerate(lines):
        if keyword in line:
            # محاولة استخراج المعلومات من هذا السطر أو السطر التالي
            return lines[i + 1] if i + 1 < len(lines) else line
    
    return "Not specified"