from django.urls import path
from . import views

urlpatterns = [
    path('ajax/load-branches/', views.load_branches, name='ajax_load_branches'),
    path('get-branches/', views.get_branches, name='get_branches'),
]
