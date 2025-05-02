
from django.db import models
from django.contrib.auth.models import User
from pages.models import AttackType


class Scenario(models.Model):
    scenario_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scenarios')
    attack_type = models.ForeignKey(AttackType, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    scenario_text = models.TextField()
    
    # حقل لتخزين البيانات المنظمة بصيغة JSON
    json_data = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        return f"Scenario {self.scenario_id} - {self.attack_type.name}"
    
    def get_questions(self):
        """استخراج الأسئلة من البيانات المخزنة بصيغة JSON"""
        if self.json_data and 'questions' in self.json_data:
            return self.json_data['questions']
        return []
    
    def get_specific_details(self):
        """استخراج التفاصيل المحددة للهجوم من البيانات المخزنة بصيغة JSON"""
        if self.json_data and 'scenario' in self.json_data and 'specificDetails' in self.json_data['scenario']:
            return self.json_data['scenario']['specificDetails']
        return {}


# نموذج لتخزين السيناريوهات الجاهزة في قاعدة البيانات
class StoredScenario(models.Model):
    id = models.AutoField(primary_key=True)
    attack_type = models.ForeignKey(AttackType, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # تخزين البيانات المنظمة بصيغة JSON
    json_data = models.JSONField()
    
    def __str__(self):
        return f"{self.title} ({self.attack_type.name})"
    
    def get_scenario_text(self):
        """استخراج نص السيناريو من البيانات المخزنة بصيغة JSON"""
        if self.json_data and 'scenario' in self.json_data and 'scenarioText' in self.json_data['scenario']:
            return self.json_data['scenario']['scenarioText']
        return ""
    
    def get_questions(self):
        """استخراج الأسئلة من البيانات المخزنة بصيغة JSON"""
        if self.json_data and 'questions' in self.json_data:
            return self.json_data['questions']
        return []


class Question(models.Model):
    question_id = models.AutoField(primary_key=True)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=50, default='multiple_choice')
    explanation = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Question {self.question_id} for Scenario {self.scenario.scenario_id}"


class Answer(models.Model):
    answer_id = models.AutoField(primary_key=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.answer_text} ({'✓' if self.is_correct else '✗'})"


class Response(models.Model):
    response_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Response {self.response_id} by {self.user.username}"


class UserScenarioResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    score = models.IntegerField()  # عدد الإجابات الصحيحة
    total_questions = models.IntegerField()  # العدد الإجمالي للأسئلة
    percentage = models.FloatField()  # النسبة المئوية للإجابات الصحيحة
    feedback = models.TextField(null=True, blank=True)  # التغذية الراجعة
    completed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.score}/{self.total_questions} ({self.percentage:.1f}%)"