from django.contrib import admin
from .models import Resident, PRNProtocol


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_number', 'date_of_birth', 'created_at']
    search_fields = ['name', 'room_number']


@admin.register(PRNProtocol)
class PRNProtocolAdmin(admin.ModelAdmin):
    list_display = ['medicine_name', 'resident', 'form', 'strength', 'created_at']
    search_fields = ['medicine_name', 'resident__name']
    list_filter = ['resident']
