from django.urls import path
from . import views

urlpatterns = [
    path('get-branches/', views.get_branches, name='get_branches'),
]
