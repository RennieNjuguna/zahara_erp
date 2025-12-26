from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    # Credit Note URLs
    path('credit-notes/', views.credit_note_list, name='credit_note_list'),
    path('credit-notes/create/step1/', views.credit_note_create_step1, name='credit_note_create_step1'),
    path('credit-notes/create/step2/', views.credit_note_create_step2, name='credit_note_create_step2'),
    path('credit-notes/create/step3/', views.credit_note_create_step3, name='credit_note_create_step3'),
    path('credit-notes/<int:credit_note_id>/', views.credit_note_detail, name='credit_note_detail'),
    path('credit-notes/<int:credit_note_id>/approve/', views.credit_note_approve, name='credit_note_approve'),

    # Invoice URLs
    path('<str:invoice_code>/', views.invoice_detail, name='invoice_detail'),
]
