from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    # Expense URLs
    path('', views.expense_list, name='expense_list'),
    path('create/', views.expense_create, name='expense_create'),
    path('<int:expense_id>/', views.expense_detail, name='expense_detail'),
    path('<int:expense_id>/edit/', views.expense_edit, name='expense_edit'),
    path('<int:expense_id>/delete/', views.expense_delete, name='expense_delete'),

    # Category URLs
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:category_id>/delete/', views.category_delete, name='category_delete'),
]
