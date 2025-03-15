from django.urls import path
from . import views
from django.shortcuts import redirect

urlpatterns = [
     path('', lambda request: redirect('login'), name='training_home'),
    path('login/', views.training_login, name='training_login'),
    path('select/', views.select_attack, name='select_attack'),
    path('scenario/<int:scenario_id>/', views.scenario, name='scenario'),
    path('feedback/<int:scenario_id>/', views.feedback, name='feedback'),
]