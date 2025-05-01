from email.utils import parsedate
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
    """
    # تهيئة API
    init_genai()

    # تحديد نموذج Gemini
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
    except Exception as e:
        print(f"Error initializing Gemini model: {str(e)}")
        return create_default_scenario(attack_type)

    prompt = f"""
    You are an expert in information security and cybersecurity. Create a realistic and comprehensive training scenario about a {attack_type} attack with 15 multiple-choice questions.
     
    ## Scenario Requirements:
    1. Provide a detailed, realistic, and comprehensive description of a {attack_type} attack in a real organizational environment
    2. The scenario must include details specific to the attack type:
    3. The scenario must be as a paragraph with 400 words or 500 words
    4. The scenario mush start with "Read the Scenario"
    5. There must not be any star * or hash # in scenario, questions and the choices and the word Questions:
    6. The scenario must include the following details:
    7. IMPORTANT: DO NOT include any introductory text like "Okay, here's a scenario..."
     
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
    2. Each question must have 4 potential options the choices must follow the format A. B. C. D. and 15 questions  
    3. Only one correct answer per question
    4. Progressive difficulty level from basic to advanced
    5. Cover various aspects of the attack: detection, prevention, response, mitigation
    6. Must include 15 questions and the choices must follow the format A. B. C. D.
    7. Number questions from 1 to 15
    8.insert tick mark (✓) next to the correct answer (don't show the tick mark in the answer options)
    9.randomize the location of correct answer in options - note that don't use same letter as correct answer in all questions 

    Example question format:
    What was the attack vector used in this scenario?
    A. Phishing email 
    B. USB drive
    C. Compromised website
    D. Malicious advertisement
    
    Please respond with the scenario first, followed by all 15 questions with their options
    
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
        
        print("Response from Gemini API: ", text_response)
        # تحويل النص إلى تنسيق منظم
        scenario_data = parse_ai_response(text_response, attack_type)
        print("....")
        print(scenario_data)

        # التحقق من جودة السيناريو
        if not scenario_data or len(scenario_data.get('scenario', {}).get('scenarioText', '').strip()) < 100:
            print("Generated scenario too short or empty")
            return create_default_scenario(attack_type)
            
        return scenario_data
            
    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        return create_default_scenario(attack_type)
def parse_ai_response_json(json_response, attack_type):
    """
    Parse JSON response from AI to extract scenario details, questions and answers.
    
    Args:
        json_response (dict): JSON response from AI containing scenario and questions
        attack_type (str): Type of attack ('ransomware', 'mitm', or 'ddos')
    
    Returns:
        dict: Dictionary containing structured scenario data and questions
    """
    # Initialize dictionary to store parsed data
    parsed_data = {
        'scenario': {
            'scenarioText': '',
            'attackType': attack_type,
            'specificDetails': {}
        },
        'questions': []
    }
    
    # Extract scenario text
    if 'scenario' in json_response:
        # If scenario is a string, use it directly
        if isinstance(json_response['scenario'], str):
            parsed_data['scenario']['scenarioText'] = json_response['scenario']
        # If scenario is a dictionary with 'scenarioText' key
        elif isinstance(json_response['scenario'], dict) and 'scenarioText' in json_response['scenario']:
            parsed_data['scenario']['scenarioText'] = json_response['scenario']['scenarioText']
    
    # Extract scenario specific details based on attack type
    if attack_type.lower() == 'ransomware':
        # Extract ransomware specific details from scenario text
        scenario_text = parsed_data['scenario']['scenarioText']
        specific_details = {}
        
        # Try to find initial infection vector
        if "InitialInfectionVector" in scenario_text:
            # Simple extraction 
            infection_vector = extract_detail(scenario_text, "InitialInfectionVector")
            specific_details['initialInfectionVector'] = infection_vector
        
        # Try to find ransom amount
        if "RansomAmount" in scenario_text:
            ransom_amount = extract_detail(scenario_text, "RansomAmount")
            specific_details['ransomAmount'] = ransom_amount
        
        # Try to find deadline
        if "Deadline" in scenario_text:
            deadline = extract_detail(scenario_text, "Deadline")
            specific_details['deadline'] = deadline
        
        parsed_data['scenario']['specificDetails'] = specific_details
    
    elif attack_type.lower() == 'mitm':
        # Extract Man-in-the-Middle specific details
        scenario_text = parsed_data['scenario']['scenarioText']
        specific_details = {}
        
        # Try to find type vector
        if "TypeVector" in scenario_text:
            type_vector = extract_detail(scenario_text, "TypeVector")
            specific_details['typeVector'] = type_vector
        
        # Try to find data intercepted
        if "DataIntercepted" in scenario_text:
            data_intercepted = extract_detail(scenario_text, "DataIntercepted")
            specific_details['dataIntercepted'] = data_intercepted
        
        parsed_data['scenario']['specificDetails'] = specific_details
    
    elif attack_type.lower() == 'ddos':
        # Extract DDoS specific details
        scenario_text = parsed_data['scenario']['scenarioText']
        specific_details = {}
        
        # Try to find type of DDoS
        if "TypeOfDDoS" in scenario_text:
            ddos_type = extract_detail(scenario_text, "TypeOfDDoS")
            specific_details['typeOfDDoS'] = ddos_type
        
        # Try to find attack vector
        if "AttackVector" in scenario_text:
            attack_vector = extract_detail(scenario_text, "AttackVector")
            specific_details['attackVector'] = attack_vector
        
        # Try to find targeted service
        if "TargetedService" in scenario_text:
            targeted_service = extract_detail(scenario_text, "TargetedService")
            specific_details['targetedService'] = targeted_service
        
        # Try to find duration
        if "Duration" in scenario_text:
            duration = extract_detail(scenario_text, "Duration")
            specific_details['duration'] = duration
        
        parsed_data['scenario']['specificDetails'] = specific_details
    
    # Extract questions
    if 'questions' in json_response and isinstance(json_response['questions'], list):
        for q_data in json_response['questions']:
            question = {}
            
            # Handle different JSON formats
            if isinstance(q_data, dict):
                # Format 1: {id: 1, question: "text", options: {A: "opt1", B: "opt2"}, answer: "A"}
                if 'question' in q_data and 'options' in q_data and 'answer' in q_data:
                    question['questionText'] = q_data['question']
                    
                    # Convert options from {A: "text", B: "text"} to list ["text", "text"]
                    options = []
                    correct_answer_index = None
                    
                    # Handle options as dictionary with letter keys
                    if isinstance(q_data['options'], dict):
                        for i, (key, value) in enumerate(q_data['options'].items()):
                            options.append(value)
                            if key == q_data['answer']:
                                correct_answer_index = i
                    
                    question['options'] = options
                    question['correctAnswerIndex'] = correct_answer_index
                    question['explanation'] = q_data.get('explanation', '')
                
                # Format 2: {questionText: "text", options: ["opt1", "opt2"], correctAnswerIndex: 0}
                elif 'questionText' in q_data and 'options' in q_data and 'correctAnswerIndex' in q_data:
                    question = q_data
            
            if question:
                parsed_data['questions'].append(question)
    
    return parsed_data

def parse_ai_response(text_response, attack_type):
    """
    تحليل استجابة النص من الذكاء الاصطناعي وتحويلها إلى تنسيق منظم
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

def extract_detail(text, keyword):
    """
    Helper function to extract specific details from scenario text.
    
    Args:
        text (str): The scenario text
        keyword (str): The keyword to search for
    
    Returns:
        str: Extracted information or default value
    """
    lines = text.split('\n')
    keyword = keyword.lower()
    
    # Try to find the keyword in the text
    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            # If found, try to extract the information from the same line or next line
            # This is a simple extraction method and might need refinement
            current_line = line.lower()
            
            # Try to extract information after the keyword in the same line
            if ":" in current_line:
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    return parts[1].strip()
            
            # If not found in the same line, check the next line
            if i + 1 < len(lines) and lines[i + 1].strip():
                return lines[i + 1].strip()
            
            # If we found the keyword but couldn't extract a value, return the line itself
            return line.strip()
    
    # If the keyword wasn't found, check for similar patterns
    for line in lines:
        if keyword.replace("_", " ").lower() in line.lower():
            # Return what seems to be the value
            parts = line.split(":", 1) if ":" in line else line.split("was", 1)
            if len(parts) > 1:
                return parts[1].strip()
    
    # If we couldn't find anything, return a default value
    return "Not specified"

# def extract_detail(text, keyword):
#     """
#     استخراج تفاصيل محددة من النص
#     """
#     # هذه دالة بسيطة لاستخراج معلومات من النص - يمكن تحسينها
#     keyword = keyword.lower()
#     lines = text.lower().split("\n")
    
#     for i, line in enumerate(lines):
#         if keyword in line:
#             # محاولة استخراج المعلومات من هذا السطر أو السطر التالي
#             return lines[i + 1] if i + 1 < len(lines) else line
    
#     return "Not specified"

def create_default_scenario(attack_type):
    """
    إنشاء سيناريو افتراضي مفصل
    """
    if attack_type.lower() == 'ransomware':
        scenario_text = """
        Read the Scenario

        TechVision Inc., a medium-sized software development company with 200 employees, experienced a devastating ransomware attack that paralyzed their operations. The attack began when a senior developer received an email appearing to be from a trusted client with an urgent project specification document attached. The document was disguised as a PDF but contained a malicious macro that, when opened, silently installed the CryptoLock ransomware. 

        The initial infection occurred on a Monday morning and went undetected for approximately 4 hours as the malware established persistence and began mapping the network. By early afternoon, the ransomware activated its encryption routine, targeting critical development files, customer databases, and backup systems across the network. The malware employed AES-256 encryption for files and RSA-2048 for the encryption keys, making decryption without the attacker's private key mathematically impossible.

        Employees first noticed issues when accessing project files became impossible, with strange .encrypted extensions appearing on all documents. Shortly after, ransom notes appeared on all affected systems demanding 35 Bitcoin (approximately $2.1 million) to be paid within 72 hours, warning that the decryption key would be destroyed after this deadline.

        Investigation revealed that the ransomware exploited several security weaknesses: outdated Windows systems missing critical security patches, insufficient network segmentation allowing lateral movement, and local admin rights granted to many employees. Most critically, TechVision's backup solution had also been compromised as it was connected to the main network and used credentials stored on a compromised domain controller.

        The company's CIO immediately assembled an incident response team, isolated affected systems, and contacted law enforcement and a specialized cybersecurity firm. The attack impacted 90% of the company's data, bringing development projects to a halt and affecting service to over 50 enterprise clients. The company faced a difficult decision between paying the ransom without guarantee of recovery or rebuilding their systems from scratch, potentially losing years of intellectual property.
        """
        specific_details = {
            "initialInfectionVector": "Phishing email with malicious document attachment",
            "ransomAmount": "$2.1 million (35 Bitcoin)",
            "deadline": "72 hours"
        }
    elif attack_type.lower() == 'ddos':
        scenario_text = """
        Read the Scenario

        GlobalStream, a popular video streaming service with approximately 5 million subscribers worldwide, experienced a severe distributed denial-of-service (DDoS) attack that crippled its services during the premiere of its most anticipated series. The attack began at 8:00 PM EST on Friday, precisely when the new season was scheduled to launch, maximizing user frustration and business impact.

        The attack was identified as a multi-vector DDoS campaign combining three primary methods: a massive UDP flood targeting the company's DNS infrastructure, a TCP SYN flood aimed at exhausting connection resources on the application servers, and a sophisticated layer 7 attack targeting specific API endpoints responsible for user authentication and content delivery.

        Traffic analysis revealed the attack originated from a botnet comprising over 200,000 compromised IoT devices including home routers, IP cameras, and smart appliances. The attack traffic peaked at an unprecedented 1.7 Tbps, overwhelming GlobalStream's standard DDoS protection measures. The geographic distribution of the attack traffic spanned 43 countries, with notable concentrations from compromised devices in Eastern Europe and Southeast Asia.

        The company's Security Operations Center initially responded by implementing rate limiting and traffic filtering, but these measures proved ineffective against the scale and complexity of the attack. The targeted services remained completely unavailable for approximately 4 hours, and experienced intermittent disruptions for an additional 9 hours until full mitigation was achieved.

        Investigation revealed that GlobalStream had recently migrated to a new content delivery network without conducting adequate load testing or implementing proper traffic scrubbing services. Additionally, their on-premise infrastructure lacked sufficient bandwidth overhead to absorb such a volumetric attack. The business impact was substantial: approximately 3.2 million concurrent users were unable to access the service during the attack, leading to massive social media backlash, subscription cancellations, and an estimated revenue loss of $4.5 million.
        """
        specific_details = {
            "typeOfDDoS": "Multi-vector (UDP flood, TCP SYN flood, Layer 7 attack)",
            "attackVector": "Botnet of 200,000 compromised IoT devices",
            "targetedService": "Video streaming platform and authentication services",
            "duration": "13 hours (4 hours complete outage, 9 hours intermittent)"
        }
    else:  # mitm
        scenario_text = """
        Read the Scenario

        FinSecure, a mid-sized financial services company, fell victim to a sophisticated Man-in-the-Middle attack that compromised sensitive client data and financial transactions. The attack began during a three-day financial technology conference where several executives and senior managers were in attendance.

        The attack vector involved a rogue Wi-Fi access point established in the hotel where the conference was held. The attackers created a fraudulent network named "Hotel_Guest_WiFi" with a stronger signal than the legitimate hotel network "Hotel_Guest_Network." When FinSecure employees connected to this rogue network, all their network traffic was intercepted before being forwarded to legitimate destinations.

        The attackers employed several techniques to execute the MitM attack: ARP spoofing to redirect traffic through their devices, SSL stripping to downgrade HTTPS connections to unencrypted HTTP where possible, and a sophisticated SSL proxy using a fraudulent certificate to intercept encrypted communications. Their toolkit included customized versions of Ettercap for traffic interception and Wireshark for packet analysis.

        During the 72-hour attack window, the attackers intercepted approximately 740 MB of data, including login credentials for the company's VPN, cloud services, and financial management platforms. They also captured email communications containing confidential client information, acquisition plans, and PDF attachments with financial statements. Most critically, the attackers intercepted and modified several wire transfer authorization requests, redirecting funds totaling $2.75 million to offshore accounts.

        The breach was only discovered when the company's CFO noticed discrepancies in transaction records upon returning to the office. The subsequent investigation revealed that 14 employees had connected to the rogue network, with 9 of them accessing sensitive company resources during that time. The company's security team determined that the attack succeeded primarily because employees disregarded the company's secure connection policy requiring the use of the corporate VPN when working remotely, and because their multi-factor authentication system excluded certain legacy applications, which became the primary entry points for the attackers.
        """
        specific_details = {
            "typeVector": "Rogue Wi-Fi access point with SSL stripping and spoofing",
            "dataIntercepted": "Login credentials, financial transactions, confidential communications"
        }

    # إنشاء أسئلة بناءً على نوع الهجوم
    questions = generate_default_questions(attack_type)
    
    return {
        "scenario": {
            "scenarioText": scenario_text.strip(),
            "attackType": attack_type,
            "specificDetails": specific_details
        },
        "questions": questions
    }

def generate_default_questions(attack_type):
    """
    إنشاء أسئلة افتراضية لسيناريو محدد
    """
    questions = []
    
    if attack_type.lower() == 'ransomware':
        questions = [
            {
                "questionText": "What was the initial infection vector used in the ransomware attack?",
                "options": [
                    "Email with malicious document attachment",
                    "USB drive",
                    "Vulnerability in the web server",
                    "Remote desktop protocol exploitation"
                ],
                "correctAnswerIndex": 0
            },
            {
                "questionText": "How much ransom was demanded by the attackers?",
                "options": [
                    "$1 million",
                    "$2.1 million (35 Bitcoin)",
                    "$3.5 million",
                    "$5 million"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What encryption algorithms were used by the CryptoLock ransomware?",
                "options": [
                    "AES-128 and RSA-1024",
                    "AES-256 and RSA-2048",
                    "Blowfish and RSA-4096",
                    "RC4 and DSA-2048"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "How long did the attackers give the company to pay the ransom?",
                "options": [
                    "24 hours",
                    "48 hours",
                    "72 hours",
                    "One week"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What percentage of the company's data was affected by the attack?",
                "options": [
                    "50%",
                    "75%",
                    "90%",
                    "100%"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What was one of the critical security weaknesses exploited by the ransomware?",
                "options": [
                    "Absence of antivirus software",
                    "Outdated Windows systems missing security patches",
                    "Employees using personal devices",
                    "Remote work policies"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "Who was the first person to be notified after the attack was discovered?",
                "options": [
                    "The CEO",
                    "The CIO",
                    "Law enforcement",
                    "The cybersecurity firm"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What was the main issue with the company's backup solution?",
                "options": [
                    "It was outdated and unreliable",
                    "It was connected to the main network and used compromised credentials",
                    "It only backed up 50% of critical data",
                    "It was offline for maintenance"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "How many employees does TechVision Inc. have?",
                "options": [
                    "100 employees",
                    "200 employees",
                    "500 employees",
                    "1000 employees"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "How many hours did it take before the ransomware attack was detected?",
                "options": [
                    "2 hours",
                    "4 hours",
                    "8 hours",
                    "12 hours"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What is the best practice for preventing ransomware spread after initial detection?",
                "options": [
                    "Install updated antivirus software",
                    "Reboot all systems",
                    "Isolate affected systems from the network",
                    "Change all passwords immediately"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What type of file extensions appeared after encryption?",
                "options": [
                    ".locked",
                    ".ransomware",
                    ".encrypted",
                    ".crypto"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "How many enterprise clients were affected by this attack?",
                "options": [
                    "Over 25 clients",
                    "Over 50 clients",
                    "Over 75 clients",
                    "Over 100 clients"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "Which of these is NOT mentioned as a security weakness in the scenario?",
                "options": [
                    "Outdated Windows systems",
                    "Insufficient network segmentation",
                    "Weak password policies",
                    "Local admin rights granted to many employees"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What day of the week did the initial infection occur?",
                "options": [
                    "Monday",
                    "Wednesday",
                    "Friday",
                    "Sunday"
                ],
                "correctAnswerIndex": 0
            }
        ]
    elif attack_type.lower() == 'ddos':
        questions = [
            {
                "questionText": "What type of DDoS attack was used against GlobalStream?",
                "options": [
                    "Single-vector UDP flood",
                    "Multi-vector attack (UDP flood, TCP SYN flood, Layer 7)",
                    "DNS amplification attack only",
                    "Slowloris attack"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What was the peak traffic volume during the attack?",
                "options": [
                    "700 Gbps",
                    "1.2 Tbps",
                    "1.7 Tbps",
                    "2.3 Tbps"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "How many IoT devices were part of the botnet used in the attack?",
                "options": [
                    "50,000 devices",
                    "100,000 devices",
                    "200,000 devices",
                    "500,000 devices"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "When did the attack begin?",
                "options": [
                    "Monday morning during business hours",
                    "Thursday afternoon during a software update",
                    "Friday at 8:00 PM EST during a premiere",
                    "Saturday during routine maintenance"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "How long did the complete service outage last?",
                "options": [
                    "2 hours",
                    "4 hours",
                    "6 hours",
                    "8 hours"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What was one of the key security oversights mentioned in the scenario?",
                "options": [
                    "Lack of employee training",
                    "No DDoS protection measures in place",
                    "Inadequate load testing after CDN migration",
                    "Using outdated server software"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "From how many countries did the attack traffic originate?",
                "options": [
                    "23 countries",
                    "33 countries",
                    "43 countries",
                    "53 countries"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What was the estimated revenue loss resulting from the attack?",
                "options": [
                    "$1.5 million",
                    "$3.0 million",
                    "$4.5 million",
                    "$6.0 million"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "Which of these was NOT mentioned as part of the botnet?",
                "options": [
                    "Home routers",
                    "IP cameras",
                    "Smart appliances",
                    "Mobile phones"
                ],
                "correctAnswerIndex": 3
            },
            {
                "questionText": "How many concurrent users were unable to access the service during the attack?",
                "options": [
                    "1.5 million users",
                    "2.8 million users",
                    "3.2 million users",
                    "4.0 million users"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What was the first mitigation measure attempted by the Security Operations Center?",
                "options": [
                    "Blocking specific IP ranges",
                    "Implementing rate limiting and traffic filtering",
                    "Increasing server capacity",
                    "Moving services to backup data centers"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "Which regions showed notable concentrations of attack traffic?",
                "options": [
                    "Western Europe and North America",
                    "Eastern Europe and Southeast Asia",
                    "South America and Africa",
                    "Central Asia and Australia"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What type of attack specifically targeted the API endpoints?",
                "options": [
                    "UDP flood",
                    "TCP SYN flood",
                    "Layer 7 attack",
                    "DNS amplification"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "Approximately how many subscribers does GlobalStream have?",
                "options": [
                    "2 million",
                    "5 million",
                    "8 million",
                    "10 million"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What was being premiered when the attack occurred?",
                "options": [
                    "A new movie",
                    "A sporting event",
                    "A new season of a popular series",
                    "A live concert"
                ],
                "correctAnswerIndex": 2
            }
        ]
    else:  # mitm
        questions = [
            {
                "questionText": "What was the primary attack vector used in this MitM attack?",
                "options": [
                    "Compromised VPN service",
                    "Rogue Wi-Fi access point",
                    "Browser extension malware",
                    "Compromised network switch"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What was the name of the rogue network created by the attackers?",
                "options": [
                    "Conference_WiFi",
                    "Free_Hotel_WiFi",
                    "Hotel_Guest_WiFi",
                    "FinSecure_Guest"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What technique was used by attackers to redirect traffic through their devices?",
                "options": [
                    "DNS poisoning",
                    "BGP hijacking",
                    "ARP spoofing",
                    "MAC flooding"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "How much money was redirected to offshore accounts during the attack?",
                "options": [
                    "$1.25 million",
                    "$2.75 million",
                    "$3.5 million",
                    "$5 million"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "How was the breach initially discovered?",
                "options": [
                    "An employee reported suspicious emails",
                    "The company's CFO noticed transaction discrepancies",
                    "The security team detected unusual network traffic",
                    "The attackers demanded a ransom"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "How long did the attack window last?",
                "options": [
                    "24 hours",
                    "48 hours",
                    "72 hours",
                    "One week"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What tools did the attackers use for traffic interception?",
                "options": [
                    "Nmap and Metasploit",
                    "Ettercap and Wireshark",
                    "Burp Suite and OWASP ZAP",
                    "Kali Linux and Aircrack-ng"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "How many employees connected to the rogue network?",
                "options": [
                    "8 employees",
                    "14 employees",
                    "22 employees",
                    "36 employees"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What security policy did employees disregard that contributed to the success of the attack?",
                "options": [
                    "Password rotation policy",
                    "Data encryption policy",
                    "Device management policy",
                    "Secure connection policy requiring VPN use"
                ],
                "correctAnswerIndex": 3
            },
            {
                "questionText": "How much data was intercepted during the attack?",
                "options": [
                    "240 MB",
                    "540 MB",
                    "740 MB",
                    "1.2 GB"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What method did the attackers use to intercept HTTPS connections?",
                "options": [
                    "TLS protocol downgrade",
                    "SSL stripping and a fraudulent certificate SSL proxy",
                    "HSTS bypass technique",
                    "Public key infrastructure compromise"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What type of company was FinSecure?",
                "options": [
                    "E-commerce retailer",
                    "Healthcare provider",
                    "Financial services company",
                    "Software development firm"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What was one technical vulnerability that allowed the attack to succeed?",
                "options": [
                    "Outdated operating systems",
                    "Multi-factor authentication excluded certain legacy applications",
                    "Misconfigured firewalls",
                    "Weak encryption standards"
                ],
                "correctAnswerIndex": 1
            },
            {
                "questionText": "What event were the employees attending when the attack occurred?",
                "options": [
                    "Annual company retreat",
                    "Sales meeting",
                    "Financial technology conference",
                    "Customer appreciation event"
                ],
                "correctAnswerIndex": 2
            },
            {
                "questionText": "What is the best defense against the type of attack described in the scenario?",
                "options": [
                    "Using incognito browsing mode",
                    "Changing passwords frequently",
                    "Always using a VPN on public networks and verifying SSL certificates",
                    "Disabling Wi-Fi on mobile devices"
                ],
                "correctAnswerIndex": 2
            }
        ]
    
    # تأكد من وجود 15 سؤال على الأقل
    while len(questions) < 15:
        index = len(questions) + 1
        questions.append({
            "questionText": f"Question {index} about {attack_type} security",
            "options": [
                f"Option A for question {index}",
                f"Option B for question {index}",
                f"Option C for question {index}",
                f"Option D for question {index}"
            ],
            "correctAnswerIndex": 0
        })
    
    return questions 