from django.contrib import admin

from .models import AuditLog, Resident


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_number', 'date_of_birth', 'created_at']
    search_fields = ['name', 'room_number', 'nhs_number']
    list_filter = ['residential_or_nursing']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'action', 'entity_type', 'entity_label', 'user']
    search_fields = ['entity_label', 'description', 'user__username']
    list_filter = ['action', 'entity_type']
    readonly_fields = ['created_at']
