from django.urls import path
from. import views

urlpatterns = [
    path('', views.schedule_list, name='schedule_list'),
    path('create/', views.schedule_create, name='schedule_create'),
    path('<int:pk>/', views.schedule_edit, name='schedule_edit'),
    path('<int:pk>/delete/', views.schedule_delete, name='schedule_delete'),
    path('<int:pk>/add-employee/', views.schedule_add_employee, name='schedule_add_employee'),
    path('<int:pk>/remove-employee/<int:user_id>/', views.schedule_remove_employee, name='schedule_remove_employee'),
    path('<int:pk>/excel/', views.schedule_excel, name='schedule_excel'),
]