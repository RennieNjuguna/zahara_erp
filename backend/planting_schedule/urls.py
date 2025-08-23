from django.urls import path
from . import views

app_name = 'planting_schedule'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Crop URLs
    path('crops/', views.crop_list, name='crop_list'),
    path('crops/create/', views.crop_create, name='crop_create'),
    path('crops/<int:pk>/', views.crop_detail, name='crop_detail'),
    path('crops/<int:pk>/edit/', views.crop_edit, name='crop_edit'),
    path('crops/<int:pk>/delete/', views.crop_delete, name='crop_delete'),

    # Farm Block URLs
    path('blocks/', views.block_list, name='block_list'),
    path('blocks/create/', views.block_create, name='block_create'),
    path('blocks/<int:pk>/', views.block_detail, name='block_detail'),
    path('blocks/<int:pk>/edit/', views.block_edit, name='block_edit'),
    path('blocks/<int:pk>/delete/', views.block_delete, name='block_delete'),
]
