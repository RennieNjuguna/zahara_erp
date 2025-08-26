from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    # Employee URLs
    path('', views.employee_list, name='employee_list'),
    path('create/', views.employee_create, name='employee_create'),
    path('<int:employee_id>/', views.employee_detail, name='employee_detail'),
    path('<int:employee_id>/edit/', views.employee_edit, name='employee_edit'),
    path('<int:employee_id>/delete/', views.employee_delete, name='employee_delete'),
]
