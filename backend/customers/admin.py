from django.contrib import admin
from .models import Customer, Branch

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code', 'preferred_currency')
    search_fields = ('name', 'short_code')

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code', 'customer')
    search_fields = ('name', 'short_code', 'customer__name')
