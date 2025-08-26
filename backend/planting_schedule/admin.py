from django.contrib import admin
from .models import Crop, FarmBlock


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ['name', 'days_to_maturity', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']


@admin.register(FarmBlock)
class FarmBlockAdmin(admin.ModelAdmin):
    list_display = ['name', 'area_acres', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
