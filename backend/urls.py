from orders.views import get_branches

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/get-branches/', get_branches, name='get_branches'),
]
