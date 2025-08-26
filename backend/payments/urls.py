from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Dashboard and overview
    path('', views.payment_dashboard, name='dashboard'),
    path('analytics/', views.payment_analytics, name='analytics'),

    # Payment management
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/create/', views.payment_create, name='payment_create'),
    path('payments/<uuid:payment_id>/', views.payment_detail, name='payment_detail'),
    path('payments/<uuid:payment_id>/edit/', views.payment_edit, name='payment_edit'),
    path('payments/<uuid:payment_id>/allocate/', views.allocate_payment, name='allocate_payment'),

    # Customer balance management
    path('balances/', views.customer_balance_list, name='customer_balance_list'),
    path('balances/<int:customer_id>/', views.customer_balance_detail, name='customer_balance_detail'),
    path('balances/<int:customer_id>/recalculate/', views.recalculate_balance, name='recalculate_balance'),

    # Account statements
    path('statements/', views.account_statement_list, name='account_statement_list'),
    path('statements/<int:statement_id>/', views.account_statement_detail, name='account_statement_detail'),
    path('statements/<int:statement_id>/pdf/', views.generate_account_statement_pdf, name='generate_account_statement_pdf'),
    path('statements/generate/<int:customer_id>/', views.generate_account_statement, name='generate_account_statement'),

    # API endpoints
    path('api/outstanding-orders/<int:customer_id>/', views.get_outstanding_orders, name='api_outstanding_orders'),
    path('api/customer-balance/<int:customer_id>/', views.get_customer_balance, name='api_customer_balance'),

    # Test endpoints
    path('test-pdf/', views.test_pdf_generation, name='test_pdf_generation'),
    path('test-html/<int:statement_id>/', views.test_html_preview, name='test_html_preview'),

    # Maintenance endpoints
    path('recalculate-statements/', views.recalculate_all_statements, name='recalculate_all_statements'),
]
