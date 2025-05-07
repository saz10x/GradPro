from django.urls import path
from . import views
from django.shortcuts import redirect

app_name = 'training'

urlpatterns = [
    path('', lambda request: redirect('training:select_attack'), name='training_home'),
    path('login/', views.training_login, name='login'),
    path('select/', views.select_attack, name='select_attack'),
    path('scenario/<int:scenario_id>/', views.scenario, name='scenario_by_id'),
    path('scenario/<str:attack_type>/', views.scenario_view, name='scenario_view'),
    
    path('submit/<str:attack_type>/', views.submit_answers, name='submit_answers'),
    path('feedback/<int:scenario_id>/', views.feedback, name='feedback'),
    path('download-feedback/<int:scenario_id>/', views.download_feedback_pdf, name='download_feedback_pdf'),
]