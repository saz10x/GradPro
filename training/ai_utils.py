import os
import json
import re
import google.generativeai as genai
from django.conf import settings


# تهيئة API
def init_genai():
    genai.configure(api_key=settings.GEMINI_API_KEY)


def generate_scenario(attack_type):
    """
    توليد سيناريو تدريبي بناءً على نوع الهجوم
    
    Args:
        attack_type (str): نوع الهجوم (ransomware, ddos, mitm)
        
    Returns:
        dict: البيانات المنظمة للسيناريو والأسئلة
    """
    # تهيئة API
    init_genai()

    # تحديد نموذج Gemini
    try:
        pass  # Add your code here
        model = genai.GenerativeModel("gemini-2.0-flash")
    except Exception as e:
        print(f"Error initializing Gemini model: {str(e)}")
        return create_default_scenario(attack_type)

    # إعداد النص البرمجي للحصول على إستجابة منظمة بصيغة JSON
    prompt = f"""
    You are an expert in information security and cybersecurity. Create a realistic and comprehensive training scenario about a {attack_type} attack with 15 multiple-choice questions.
     
    1. Provide a detailed, realistic, and comprehensive description of a {attack_type} attack in a real organizational environment
2. The scenario must be clear and concise, around 700 words
3. Do NOT include phrases like "Read the Scenario" or other formatting instructions
5. The scenario should naturally include these details without explicitly labeling them:

   - For Ransomware: infection vector, ransom amount, payment deadline
   - For Man-in-the-Middle: attack vector type, type of intercepted data
   - For DDoS: type of DDoS attack, attack vector, targeted service, duration
     
  ## Question Requirements:
    1. 15 multiple-choice questions directly related to the scenario
    2. Each question must have 4 potential options the choices must follow the format A. B. C. D. and 15 questions  
    3. Only one correct answer per question
    4. Progressive difficulty level from basic to advanced
    5. Cover various aspects of the attack: detection, prevention, response, mitigation
    6. Must include 15 questions and the choices must follow the format A. B. C. D.
    7. Number questions from 1 to 15
    9.randomize the location of correct answer in options - note that don't use same letter as correct answer in all questions 
    
    ## Output Format:
    You must format your response as a JSON object with the following structure:
    
    {{
      "scenario": "The full scenario text here with relevant details",
      "questions": [
        {{
          "id": 1,
          "question": "Question text here?",
          "options": {{
            "A": "First option",
            "B": "Second option",
            "C": "Third option",
            "D": "Fourth option"
          }},
          "answer": "A",

        }},
        // ... more questions
      ]
    }}
    
    IMPORTANT: Respond ONLY with the JSON object and no additional text.
    """
    try:
        # إرسال الطلب إلى Gemini API
        response = model.generate_content(prompt)
        
        # تحليل النص المستلم
        text_response = response.text
        
        # التحقق من طول الاستجابة
        if not text_response or len(text_response) < 100:
            print("Empty or very short response from Gemini API")
            return create_default_scenario(attack_type)
        
        # محاولة تحليل الاستجابة كـ JSON
        try:
            # إزالة محدد الكود JSON إذا وجد
            json_text = re.sub(r'```json|```', '', text_response).strip()
            
            # التحقق من أن النص يبدأ بـ {
            if not json_text.startswith('{'):
                # البحث عن أول { في النص
                start_idx = json_text.find('{')
                if start_idx != -1:
                    json_text = json_text[start_idx:]
            
            # التحقق من أن النص ينتهي بـ }
            if not json_text.endswith('}'):
                # البحث عن آخر } في النص
                end_idx = json_text.rfind('}')
                if end_idx != -1:
                    json_text = json_text[:end_idx+1]
            
            # تحليل النص كـ JSON
            json_response = json.loads(json_text)
            
            # تحويل الاستجابة إلى الهيكل المطلوب
            parsed_data = parse_ai_response_json(json_response, attack_type)
            
            # التحقق من جودة البيانات المستخرجة
            if not parsed_data or len(parsed_data.get('scenario', {}).get('scenarioText', '').strip()) < 100:
                print("Generated scenario too short or empty after parsing")
                return create_default_scenario(attack_type)
                
            return parsed_data
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {str(e)}")
            # إذا فشل تحليل JSON، حاول استخدام طريقة التحليل النصي التقليدية
            parsed_data = parse_ai_response(text_response, attack_type)
            return parsed_data
            
    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        return create_default_scenario(attack_type)


def parse_ai_response_json(json_response, attack_type):
    # التأكد من أن الاستجابة كائن JSON وليست نص
    if isinstance(json_response, str):
        try:
            json_response = json.loads(json_response)
        except:
            # إذا فشل التحليل، أعد استجابة افتراضية منظمة
            return {
                'scenario': {
                    'scenarioText': "Error parsing AI response. Please try again.",
                    'attackType': attack_type,
                    'specificDetails': {}
                },
                'questions': []
            }
    """
    
    تحليل استجابة JSON من الذكاء الاصطناعي لاستخراج تفاصيل السيناريو والأسئلة والإجابات
    
    Args:
        json_response (dict): استجابة JSON من الذكاء الاصطناعي
        attack_type (str): نوع الهجوم (ransomware, mitm, ddos)
    
    Returns:
        dict: قاموس يحتوي على بيانات السيناريو المنظمة والأسئلة
    """
    
    # تهيئة قاموس لتخزين البيانات المستخرجة
    parsed_data = {
        'scenario': {
            'scenarioText': '',
            'attackType': attack_type,
            'specificDetails': {}
        },
        'questions': []
    }
    
    # استخراج نص السيناريو
   # استخراج نص السيناريو
    if 'scenario' in json_response:
    # إذا كان السيناريو عبارة عن نص
        if isinstance(json_response['scenario'], str):
        # تنظيف النص من أي علامات JSON أو نصوص غير مرغوبة
            scenario_text = json_response['scenario']
            scenario_text = re.sub(r'```json|```', '', scenario_text)
            scenario_text = re.sub(r'Read the Scenario', '', scenario_text, flags=re.IGNORECASE)
            scenario_text = scenario_text.strip()
            parsed_data['scenario']['scenarioText'] = scenario_text
    # إذا كان السيناريو قاموس يحتوي على مفتاح scenarioText
    elif isinstance(json_response['scenario'], dict) and 'scenarioText' in json_response['scenario']:
        scenario_text = json_response['scenario']['scenarioText']
        scenario_text = re.sub(r'```json|```', '', scenario_text)
        scenario_text = re.sub(r'Read the Scenario', '', scenario_text, flags=re.IGNORECASE)
        scenario_text = scenario_text.strip()
        parsed_data['scenario']['scenarioText'] = scenario_text
    
    # استخراج التفاصيل المحددة بناءً على نوع الهجوم
    scenario_text = parsed_data['scenario']['scenarioText']
    
    if attack_type.lower() == 'ransomware':
        specific_details = {}
        
        # استخراج متجه العدوى الأولي
        if "InitialInfectionVector" in scenario_text:
            infection_vector = extract_detail(scenario_text, "InitialInfectionVector")
            specific_details['initialInfectionVector'] = infection_vector
        
        # استخراج المبلغ المطلوب كفدية
        if "RansomAmount" in scenario_text:
            ransom_amount = extract_detail(scenario_text, "RansomAmount")
            specific_details['ransomAmount'] = ransom_amount
        
        # استخراج الموعد النهائي
        if "Deadline" in scenario_text:
            deadline = extract_detail(scenario_text, "Deadline")
            specific_details['deadline'] = deadline
        
        parsed_data['scenario']['specificDetails'] = specific_details
    
    elif attack_type.lower() == 'mitm':
        specific_details = {}
        
        # استخراج نوع متجه الهجوم
        if "TypeVector" in scenario_text:
            type_vector = extract_detail(scenario_text, "TypeVector")
            specific_details['typeVector'] = type_vector
        
        # استخراج البيانات المعترضة
        if "DataIntercepted" in scenario_text:
            data_intercepted = extract_detail(scenario_text, "DataIntercepted")
            specific_details['dataIntercepted'] = data_intercepted
        
        parsed_data['scenario']['specificDetails'] = specific_details
    
    elif attack_type.lower() == 'ddos':
        specific_details = {}
        
        # استخراج نوع هجوم DDoS
        if "TypeOfDDoS" in scenario_text:
            ddos_type = extract_detail(scenario_text, "TypeOfDDoS")
            specific_details['typeOfDDoS'] = ddos_type
        
        # استخراج متجه الهجوم
        if "AttackVector" in scenario_text:
            attack_vector = extract_detail(scenario_text, "AttackVector")
            specific_details['attackVector'] = attack_vector
        
        # استخراج الخدمة المستهدفة
        if "TargetedService" in scenario_text:
            targeted_service = extract_detail(scenario_text, "TargetedService")
            specific_details['targetedService'] = targeted_service
        
        # استخراج مدة الهجوم
        if "Duration" in scenario_text:
            duration = extract_detail(scenario_text, "Duration")
            specific_details['duration'] = duration
        
        parsed_data['scenario']['specificDetails'] = specific_details
    
    # استخراج الأسئلة
    if 'questions' in json_response and isinstance(json_response['questions'], list):
        for q_data in json_response['questions']:
            question = {}
            
            # التعامل مع تنسيقات JSON المختلفة
            if isinstance(q_data, dict):
                # التنسيق 1: {id: 1, question: "text", options: {A: "opt1", B: "opt2"}, answer: "A"}
                if 'question' in q_data and 'options' in q_data and 'answer' in q_data:
                    question['questionText'] = q_data['question']
                    
                    # تحويل الخيارات من {A: "نص", B: "نص"} إلى قائمة ["نص", "نص"]
                    options = []
                    correct_answer_index = None
                    
                    # التعامل مع الخيارات كقاموس بمفاتيح حرفية
                    if isinstance(q_data['options'], dict):
                        for i, (key, value) in enumerate(q_data['options'].items()):
                            options.append(value)
                            if key == q_data['answer']:
                                correct_answer_index = i
                    
                    question['options'] = options
                    question['correctAnswerIndex'] = correct_answer_index
                    question['explanation'] = q_data.get('explanation', '')
                
                # التنسيق 2: {questionText: "text", options: ["opt1", "opt2"], correctAnswerIndex: 0}
                elif 'questionText' in q_data and 'options' in q_data and 'correctAnswerIndex' in q_data:
                    question = q_data
            
            if question:
                parsed_data['questions'].append(question)
    
    return parsed_data


def extract_detail(text, keyword):
    """
    استخراج تفاصيل محددة من نص السيناريو
    
    Args:
        text (str): نص السيناريو
        keyword (str): الكلمة المفتاحية للبحث عنها
    
    Returns:
        str: المعلومات المستخرجة أو قيمة افتراضية
    """
    lines = text.split('\n')
    keyword = keyword.lower()
    
    # البحث عن الكلمة المفتاحية في النص
    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            # إذا وجدت، حاول استخراج المعلومات من نفس السطر أو السطر التالي
            current_line = line.lower()
            
            # حاول استخراج المعلومات بعد الكلمة المفتاحية في نفس السطر
            if ":" in current_line:
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    return parts[1].strip()
            
            # إذا لم يتم العثور على المعلومات في نفس السطر، تحقق من السطر التالي
            if i + 1 < len(lines) and lines[i + 1].strip():
                return lines[i + 1].strip()
            
            # إذا وجدنا الكلمة المفتاحية ولكن لم نتمكن من استخراج قيمة، أعد السطر نفسه
            return line.strip()
    
    # إذا لم يتم العثور على الكلمة المفتاحية، تحقق من أنماط مشابهة
    for line in lines:
        if keyword.replace("_", " ").lower() in line.lower():
            # إعادة ما يبدو أنه القيمة
            parts = line.split(":", 1) if ":" in line else line.split("was", 1)
            if len(parts) > 1:
                return parts[1].strip()
    
    # إذا لم نتمكن من العثور على أي شيء، أعد قيمة افتراضية
    return "Not specified"


def parse_ai_response(text_response, attack_type):
    """
    تحليل نص الاستجابة من الذكاء الاصطناعي عندما يفشل تحليل JSON
    
    Args:
        text_response (str): نص الاستجابة
        attack_type (str): نوع الهجوم
    
    Returns:
        dict: البيانات المستخرجة
    """
    # تقسيم النص إلى سيناريو وأسئلة
    lines = text_response.split('\n')
    
    # استخراج السيناريو
    scenario_text = ""
    question_section_start = False
    
    for i, line in enumerate(lines):
        # إذا وصلنا إلى قسم الأسئلة، توقف عن جمع نص السيناريو
        if re.search(r'^\s*\d+[\.)]\s+', line) or re.search(r'^\s*Question\s+\d+[\:.]', line, re.IGNORECASE):
            question_section_start = True
            break
        
        # إذا لم نصل إلى قسم الأسئلة، أضف السطر إلى نص السيناريو
        if not question_section_start:
            scenario_text += line + "\n"
    
    # تنظيف السيناريو من العبارات غير المرغوبة
    scenario_text = re.sub(r'Okay,\s+here\'s\s+a\s+comprehensive.*?scenario.*?:', '', scenario_text, flags=re.IGNORECASE)
    scenario_text = re.sub(r'\*\*Scenario:\*\*', '', scenario_text, flags=re.IGNORECASE)
    scenario_text = re.sub(r'\*\*\*Scenario:\*\*\*', '', scenario_text, flags=re.IGNORECASE)
    
    # استخراج خصائص السيناريو الإضافية
    specific_details = {}
    
    if attack_type.lower() == 'ransomware':
        if "infection vector" in text_response.lower():
            specific_details["initialInfectionVector"] = extract_detail(text_response, "infection vector")
        if "ransom" in text_response.lower() and "amount" in text_response.lower():
            specific_details["ransomAmount"] = extract_detail(text_response, "ransom amount")
        if "deadline" in text_response.lower():
            specific_details["deadline"] = extract_detail(text_response, "deadline")
            
    elif attack_type.lower() == 'mitm':
        if "vector" in text_response.lower():
            specific_details["typeVector"] = extract_detail(text_response, "attack vector")
        if "intercept" in text_response.lower():
            specific_details["dataIntercepted"] = extract_detail(text_response, "data intercepted")
            
    elif attack_type.lower() == 'ddos':
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
    current_options = []
    
    # أنماط البحث
    question_pattern = re.compile(r'(?:Question\s+(\d+)|(\d+)[\.\)])\s*(.*)', re.IGNORECASE)
    option_pattern = re.compile(r'([A-D])[\.\)]\s*(.*)', re.IGNORECASE)
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:  # تخطي السطور الفارغة
            i += 1
            continue
        
        # البحث عن بداية سؤال جديد
        question_match = question_pattern.match(line)
        if question_match:
            # إذا كان هناك سؤال حالي، أضفه إلى القائمة قبل البدء بسؤال جديد
            if current_question and current_options:
                # التأكد من وجود 4 خيارات فقط
                while len(current_options) > 4:
                    current_options.pop()
                while len(current_options) < 4:
                    current_options.append(f"Option {len(current_options) + 1}")
                
                # تحديد الإجابة الصحيحة إذا لم تكن محددة
                if 'correctAnswerIndex' not in current_question or current_question['correctAnswerIndex'] is None:
                    current_question['correctAnswerIndex'] = 0
                
                current_question['options'] = current_options
                questions.append(current_question)
                current_options = []
            
            # استخراج معلومات السؤال الجديد
            q_num = question_match.group(1) or question_match.group(2)
            q_text = question_match.group(3)
            
            # إذا كان نص السؤال فارغًا، حاول الحصول عليه من السطر التالي
            if not q_text and i + 1 < len(lines) and not option_pattern.match(lines[i + 1].strip()):
                i += 1
                q_text = lines[i].strip()
            
            current_question = {
                'questionText': q_text,
                'correctAnswerIndex': None
            }
            
        # البحث عن خيارات الإجابة
        elif current_question and option_pattern.match(line):
            option_match = option_pattern.match(line)
            option_letter = option_match.group(1)
            option_text = option_match.group(2)
            
            # تحديد ما إذا كان هذا هو الخيار الصحيح
            is_correct = ('correct' in line.lower() or '✓' in line)
            
            # إزالة علامات الإجابة الصحيحة من النص
            option_text = re.sub(r'\s*\(correct\)\s*', '', option_text, flags=re.IGNORECASE)
            option_text = re.sub(r'\s*✓\s*', '', option_text)
            
            current_options.append(option_text)
            
            if is_correct:
                current_question['correctAnswerIndex'] = len(current_options) - 1
        
        i += 1
    
    # إضافة السؤال الأخير إذا كان موجودًا
    if current_question and current_options:
        # التأكد من وجود 4 خيارات فقط
        while len(current_options) > 4:
            current_options.pop()
        while len(current_options) < 4:
            current_options.append(f"Option {len(current_options) + 1}")
        
        # تحديد الإجابة الصحيحة إذا لم تكن محددة
        if 'correctAnswerIndex' not in current_question or current_question['correctAnswerIndex'] is None:
            current_question['correctAnswerIndex'] = 0
        
        current_question['options'] = current_options
        questions.append(current_question)
    
    # التأكد من وجود 15 سؤال
    while len(questions) < 15:
        question_number = len(questions) + 1
        questions.append({
            'questionText': f'Question {question_number} about {attack_type}',
            'options': [
                f'Option 1 for question {question_number}',
                f'Option 2 for question {question_number}',
                f'Option 3 for question {question_number}',
                f'Option 4 for question {question_number}'
            ],
            'correctAnswerIndex': 0
        })
    
    # إذا كان هناك أكثر من 15 سؤال، احتفظ فقط بالـ 15 الأولى
    questions = questions[:15]
    
    return {
        "scenario": {
            "scenarioText": scenario_text.strip(),
            "attackType": attack_type,
            "specificDetails": specific_details
        },
        "questions": questions
    }


def create_default_scenario(attack_type):
    """
    إنشاء سيناريو افتراضي عندما يفشل الحصول على سيناريو من الذكاء الاصطناعي
    
    Args:
        attack_type (str): نوع الهجوم
    
    Returns:
        dict: بيانات السيناريو الافتراضي
    """
    if attack_type.lower() == 'ransomware':
        scenario_text = """
        Read the Scenario

        TechVision Inc., a medium-sized software development company with 200 employees, experienced a devastating ransomware attack that paralyzed their operations. The attack began when a senior developer received an email appearing to be from a trusted client with an urgent project specification document attached. The document was disguised as a PDF but contained a malicious macro that, when opened, silently installed the CryptoLock ransomware. 

        The initial infection occurred on a Monday morning and went undetected for approximately 4 hours as the malware established persistence and began mapping the network. By early afternoon, the ransomware activated its encryption routine, targeting critical development files, customer databases, and backup systems across the network. The malware employed AES-256 encryption for files and RSA-2048 for the encryption keys, making decryption without the attacker's private key mathematically impossible.

        Employees first noticed issues when accessing project files became impossible, with strange .encrypted extensions appearing on all documents. Shortly after, ransom notes appeared on all affected systems demanding 35 Bitcoin (approximately $2.1 million) to be paid within 72 hours, warning that the decryption key would be destroyed after this deadline.

        Investigation revealed that the ransomware exploited several security weaknesses: outdated Windows systems missing critical security patches, insufficient network segmentation allowing lateral movement, and local admin rights granted to many employees. Most critically, TechVision's backup solution had also been compromised as it was connected to the main network and used credentials stored on a compromised domain controller.

        The company's CIO immediately assembled an incident response team, isolated affected systems, and contacted law enforcement and a specialized cybersecurity firm. The attack impacted 90% of the company's data, bringing development projects to a halt and affecting service to over 50 enterprise clients. The company faced a difficult decision between paying the ransom without guarantee of recovery or rebuilding their systems from scratch, potentially losing years of intellectual property."""
