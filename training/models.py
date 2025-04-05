from django.db import models
from django.contrib.auth.models import User
from pages.models import AttackType

class Scenario(models.Model):
    scenario_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scenarios')
    attack_type = models.ForeignKey(AttackType, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    scenario_text = models.TextField()
    
    def __str__(self):
        return f"Scenario {self.scenario_id}"

# نموذج مجرد يحتوي على الحقول المشتركة
class ScenarioDetailsBase(models.Model):
    scenario = models.OneToOneField(Scenario, on_delete=models.CASCADE, primary_key=True)
    
    class Meta:
        abstract = True  # هذا يجعل النموذج مجردًا - لن ينشئ جدولًا

class RansomwareScenario(ScenarioDetailsBase):
    initial_infection_vector = models.CharField(max_length=200)
    ransom_amount = models.DecimalField(max_digits=10, decimal_places=2)
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