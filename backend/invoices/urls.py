from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    # Credit Note URLs (must come before generic invoice pattern)
    path('credit-notes/', views.credit_note_list, name='credit_note_list'),
    path('credit-notes/create/', views.credit_note_create, name='credit_note_create'),
    path('credit-notes/bulk-create/', views.bulk_credit_note_create, name='bulk_credit_note_create'),
    path('credit-notes/<int:credit_note_id>/', views.credit_note_detail, name='credit_note_detail'),
    path('credit-notes/<int:credit_note_id>/edit/', views.credit_note_edit, name='credit_note_edit'),
    path('credit-notes/<int:credit_note_id>/cancel/', views.credit_note_cancel, name='credit_note_cancel'),
    path('credit-notes/<int:credit_note_id>/add-items/', views.credit_note_add_items, name='credit_note_add_items'),
    path('credit-notes/<int:credit_note_id>/export/', views.credit_note_export, name='credit_note_export'),

    # AJAX endpoints
    path('ajax/order-items/', views.get_order_items_ajax, name='get_order_items_ajax'),
    path('ajax/customer-orders/', views.get_customer_orders_ajax, name='get_customer_orders_ajax'),

    # Invoice URLs (must come after more specific patterns)
    path('<str:invoice_code>/', views.invoice_detail, name='invoice_detail'),
]
