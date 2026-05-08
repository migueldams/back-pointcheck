from django.urls import path
from .views import dashboard_stats, employee_stats, export_attendance_excel

urlpatterns = [
    path('dashboard/', dashboard_stats, name='dashboard_stats'),
    path('employee/<uuid:user_id>/', employee_stats, name='employee_stats'),
    path('export/excel/', export_attendance_excel, name='export_excel'),
]
