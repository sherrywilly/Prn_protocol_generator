from django.urls import path
from . import views

urlpatterns = [
    # Residents
    path('', views.resident_list, name='resident_list'),
    path('residents/', views.resident_list, name='resident_list_alt'),
    path('residents/add/', views.resident_create, name='resident_create'),
    path('residents/<int:pk>/', views.resident_detail, name='resident_detail'),
    path('residents/<int:pk>/profile/', views.resident_profile, name='resident_profile'),
    path('residents/<int:pk>/edit/', views.resident_edit, name='resident_edit'),
    path('residents/<int:pk>/delete/', views.resident_delete, name='resident_delete'),
    path('residents/<int:resident_pk>/protocols/', views.protocol_list, name='protocol_list'),
    path('residents/<int:resident_pk>/protocols/add/', views.protocol_create, name='protocol_create'),
    # Protocols
    path('protocols/<int:pk>/', views.protocol_detail, name='protocol_detail'),
    path('protocols/<int:pk>/edit/', views.protocol_edit, name='protocol_edit'),
    path('protocols/<int:pk>/delete/', views.protocol_delete, name='protocol_delete'),
    path('protocols/<int:pk>/pdf/', views.protocol_pdf, name='protocol_pdf'),
    path('protocols/<int:pk>/docx/', views.protocol_docx, name='protocol_docx'),
    # AI
    path('api/protocol-autofill/', views.protocol_autofill_by_medicine, name='protocol_autofill_by_medicine'),
    path('api/ai-suggest/', views.ai_suggest, name='ai_suggest'),
]
