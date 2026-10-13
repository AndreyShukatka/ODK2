from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('journal/', views.journal, name='journal'),
    path('add/', views.add_record, name='add_record'),
    path('add-record/', views.add_record, name='add_record_alt'),  # для формы с дашборда
    path('add-detail/', views.add_detail, name='add_detail'),
    path('add-operation/', views.add_operation, name='add_operation'),
    path('kit/<int:kit_id>/', views.kit_detail, name='kit_detail'),
    path('close/', views.close_shift, name='close_shift'),

    # API для блока + Закрыть работу как на скринах
    path('api/operations/', views.api_operations, name='api_operations'),
    path('api/kits/', views.api_kits, name='api_kits'),
    path('api/remaining/', views.api_remaining, name='api_remaining'),
]