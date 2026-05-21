from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('login/submit/', views.login_submit, name='login_submit'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.resident_list, name='resident_list'),
    path('residents/', views.resident_list, name='resident_list_alt'),
    path('residents/add/', views.resident_create, name='resident_create'),
    path('residents/import/', views.resident_import, name='resident_import'),
    path('residents/import/template/', views.resident_import_template, name='resident_import_template'),
    path('residents/<int:pk>/', views.resident_detail, name='resident_detail'),
    path('residents/<int:pk>/profile/', views.resident_profile, name='resident_profile'),
    path('residents/<int:pk>/edit/', views.resident_edit, name='resident_edit'),
    path('residents/<int:pk>/delete/', views.resident_delete, name='resident_delete'),
    path('residents/<int:pk>/pdf/', views.resident_pdf, name='resident_pdf'),
    path('residents/<int:pk>/docx/', views.resident_docx, name='resident_docx'),
    path('residents/<int:pk>/print/', views.resident_print, name='resident_print'),
    path('api/resident-ai-assist/', views.resident_ai_assist, name='resident_ai_assist'),
]
