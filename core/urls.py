from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('login/submit/', views.login_submit, name='login_submit'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.resident_list, name='resident_list'),
    path('residents/', views.resident_list, name='resident_list_alt'),
    path('residents/add/', views.resident_create, name='resident_create'),
    path('residents/<int:pk>/', views.resident_detail, name='resident_detail'),
    path('residents/<int:pk>/profile/', views.resident_profile, name='resident_profile'),
    path('residents/<int:pk>/edit/', views.resident_edit, name='resident_edit'),
    path('residents/<int:pk>/delete/', views.resident_delete, name='resident_delete'),
    path('residents/<int:pk>/review/', views.resident_mark_reviewed, name='resident_mark_reviewed'),
    path('residents/<int:pk>/pdf/', views.resident_pdf, name='resident_pdf'),
    path('residents/<int:pk>/docx/', views.resident_docx, name='resident_docx'),
    path('residents/<int:pk>/print/', views.resident_print, name='resident_print'),
    path('residents/<int:resident_pk>/protocols/', views.protocol_list, name='protocol_list'),
    path('residents/<int:resident_pk>/protocols/add/', views.protocol_create, name='protocol_create'),
    path('protocols/<int:pk>/', views.protocol_detail, name='protocol_detail'),
    path('protocols/<int:pk>/edit/', views.protocol_edit, name='protocol_edit'),
    path('protocols/<int:pk>/delete/', views.protocol_delete, name='protocol_delete'),
    path('protocols/<int:pk>/pdf/', views.protocol_pdf, name='protocol_pdf'),
    path('protocols/<int:pk>/docx/', views.protocol_docx, name='protocol_docx'),
    path('api/protocol-autofill/', views.protocol_autofill_by_medicine, name='protocol_autofill_by_medicine'),
    path('api/ai-suggest/', views.ai_suggest, name='ai_suggest'),
    path('api/resident-ai-assist/', views.resident_ai_assist, name='resident_ai_assist'),
]
