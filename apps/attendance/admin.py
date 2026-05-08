from django.contrib import admin
from .models import AttendanceRecord, DailyAttendance, LeaveRequest, DisciplinaryAction


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'check_type', 'timestamp', 'status', 'minutes_late', 'is_within_geofence']
    list_filter = ['check_type', 'status', 'is_within_geofence', 'company']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    date_hierarchy = 'timestamp'


@admin.register(DailyAttendance)
class DailyAttendanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'status', 'check_in_time', 'check_out_time', 'total_hours', 'minutes_late']
    list_filter = ['status', 'date', 'company']
    date_hierarchy = 'date'


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'leave_type', 'start_date', 'end_date', 'status']
    list_filter = ['status', 'leave_type']


@admin.register(DisciplinaryAction)
class DisciplinaryActionAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'severity', 'issued_by', 'created_at', 'is_acknowledged']
    list_filter = ['action_type', 'severity', 'is_acknowledged']
