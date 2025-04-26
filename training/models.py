from django.db import models
from django.contrib.auth.models import User
from pages.models import AttackType


class Scenario(models.Model):
    scenario_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scenarios')
    attack_type = models.ForeignKey(AttackType, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    scenario_text = models.TextField()
    
    # حقل جديد لتخزين البيانات بصيغة JSON
    json_data = models.JSONField(null=True, blank=True)
    
 
    ai_response = models.JSONField(null=True, blank=True)
    raw_response = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Scenario {self.scenario_id}"
    
    def get_questions(self):
        """استخراج الأسئلة من البيانات المخزنة بصيغة JSON"""
        if self.json_data and 'questions' in self.json_data:
            return self.json_data['questions']
        # استرجاع بالطريقة القديمة كخطة بديلة
        elif self.ai_response and 'questions' in self.ai_response:
            return self.ai_response['questions']
        return []

# نموذج مجرد يحتوي على الحقول المشتركة
class ScenarioDetailsBase(models.Model):
    scenario = models.OneToOneField(Scenario, on_delete=models.CASCADE, primary_key=True)
    
    class Meta:
        abstract = True  # هذا يجعل النموذج مجردًا - لن ينشئ جدولًا

class RansomwareScenario(ScenarioDetailsBase):
    initial_infection_vector = models.CharField(max_length=200)
    ransom_amount_text = models.CharField(max_length=200, default='')  # قيمة نصية للفدية
    ransom_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # القيمة الرقمية
    deadline = models.DateTimeField()
    
    def __str__(self):
        return f"Ransomware Scenario {self.scenario.scenario_id}"

class MitMScenario(ScenarioDetailsBase):
    type_vector = models.CharField(max_length=200)
    data_intercepted = models.TextField()
    
    def __str__(self):
        return f"MitM Scenario {self.scenario.scenario_id}"

class DDoSScenario(ScenarioDetailsBase):
    type_of_ddos = models.CharField(max_length=100)
    attack_vector = models.CharField(max_length=200)
    targeted_service = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    
    def __str__(self):
        return f"DDoS Scenario {self.scenario.scenario_id}"

class Question(models.Model):
    question_id = models.AutoField(primary_key=True)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=50, default='multiple_choice')
    
    # حقل لتخزين شرح الإجابة الصحيحة
    explanation = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Question {self.question_id} for Scenario {self.scenario.scenario_id}"

class Answer(models.Model):
    answer_id = models.AutoField(primary_key=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.answer_text

class Response(models.Model):
    response_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Response {self.response_id} by {self.user.username}"

# نموذج إضافي لتخزين نتيجة المستخدم الكاملة للسيناريو
class UserScenarioResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    score = models.IntegerField()  # عدد الإجابات الصحيحة
    total_questions = models.IntegerField()  # العدد الإجمالي للأسئلة
    percentage = models.FloatField()  # النسبة المئوية للإجابات الصحيحة
    feedback = models.TextField(null=True, blank=True)  # التغذية الراجعة المولدة من الذكاء الاصطناعي
    completed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.score}/{self.total_questions} ({self.percentage:.1f}%)"
    
    # store the scenario in database
class StoredScenario(models.Model):
    id = models.AutoField(primary_key=True)
    attack_type = models.ForeignKey(AttackType, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # تخزين كل البيانات بصيغة JSON
    json_data = models.JSONField()
    
    def __str__(self):
        return f"{self.attack_type.name} - {self.title}"