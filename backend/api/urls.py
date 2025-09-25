from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from . import views

# Create router
router = DefaultRouter()

# Register viewsets
router.register(r'customers', views.CustomerViewSet)
router.register(r'branches', views.BranchViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'customer-product-prices', views.CustomerProductPriceViewSet)
router.register(r'orders', views.OrderViewSet)
router.register(r'order-items', views.OrderItemViewSet)
router.register(r'order-defaults', views.CustomerOrderDefaultsViewSet)
router.register(r'payments', views.PaymentViewSet)
router.register(r'payment-types', views.PaymentTypeViewSet)
router.register(r'customer-balances', views.CustomerBalanceViewSet)
router.register(r'account-statements', views.AccountStatementViewSet)
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'credit-notes', views.CreditNoteViewSet)
router.register(r'credit-note-items', views.CreditNoteItemViewSet)
router.register(r'expenses', views.ExpenseViewSet)
router.register(r'expense-categories', views.ExpenseCategoryViewSet)
router.register(r'expense-attachments', views.ExpenseAttachmentViewSet)
router.register(r'employees', views.EmployeeViewSet)
router.register(r'crops', views.CropViewSet)
router.register(r'farm-blocks', views.FarmBlockViewSet)

# API URL patterns
urlpatterns = [
    # JWT Authentication
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Legacy token authentication
    path('auth/legacy-token/', obtain_auth_token, name='api_token_auth'),

    # Analytics endpoints
    path('analytics/dashboard/', views.DashboardStatsView.as_view(), name='dashboard_stats'),
    path('analytics/sales/', views.SalesAnalyticsView.as_view(), name='sales_analytics'),
    path('analytics/payments/', views.PaymentAnalyticsView.as_view(), name='payment_analytics'),

    # Include router URLs
    path('', include(router.urls)),
]


