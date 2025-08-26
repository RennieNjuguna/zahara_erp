from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Product URLs
    path('', views.product_list, name='product_list'),
    path('create/', views.product_create, name='product_create'),
    path('<int:product_id>/', views.product_detail, name='product_detail'),
    path('<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('<int:product_id>/delete/', views.product_delete, name='product_delete'),
    
    # Price URLs
    path('<int:product_id>/prices/create/', views.price_create, name='price_create'),
    path('prices/<int:price_id>/edit/', views.price_edit, name='price_edit'),
    path('prices/<int:price_id>/delete/', views.price_delete, name='price_delete'),
]
