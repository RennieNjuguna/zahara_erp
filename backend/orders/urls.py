from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # UI pages
    path('', views.order_list, name='order_list'),
    path('create/', views.order_create, name='order_create'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('<int:order_id>/edit/', views.order_edit, name='order_edit'),
    path('<int:order_id>/items/add/', views.order_item_add, name='order_item_add'),
    path('items/<int:item_id>/delete/', views.order_item_delete, name='order_item_delete'),

    # Missed Sales
    path('missed-sales/', views.missed_sales_list, name='missed_sales_list'),
    path('missed-sales/create/', views.missed_sale_create, name='missed_sale_create'),
    path('missed-sales/<int:pk>/edit/', views.missed_sale_edit, name='missed_sale_edit'),
    path('missed-sales/<int:pk>/delete/', views.missed_sale_delete, name='missed_sale_delete'),

    # AJAX helpers
    path('get-branches/', views.get_branches, name='get_branches'),
    path('get-orders/', views.get_orders, name='get_orders'),
    path('get-defaults/', views.get_defaults, name='get_defaults'),
    path('get-customer-pricing/', views.get_customer_pricing, name='get_customer_pricing'),
]
