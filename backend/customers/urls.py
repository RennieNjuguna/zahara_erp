from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Customer URLs
    path('', views.customer_list, name='customer_list'),
    path('create/', views.customer_create, name='customer_create'),
    path('<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('<int:customer_id>/edit/', views.customer_edit, name='customer_edit'),
    path('<int:customer_id>/delete/', views.customer_delete, name='customer_delete'),
    
    # Branch URLs
    path('<int:customer_id>/branches/create/', views.branch_create, name='branch_create'),
    path('branches/<int:branch_id>/edit/', views.branch_edit, name='branch_edit'),
    path('branches/<int:branch_id>/delete/', views.branch_delete, name='branch_delete'),
]
