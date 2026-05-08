"""Serializers pour le pointage"""
from rest_framework import serializers
from .models import AttendanceRecord, DailyAttendance, LeaveRequest, DisciplinaryAction


class AttendanceRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    department_name = serializers.CharField(source='user.department.name', read_only=True)
    check_type_display = serializers.CharField(source='get_check_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'user', 'user_name', 'user_avatar', 'department_name',
            'check_type', 'check_type_display', 'timestamp',
            'status', 'status_display', 'latitude', 'longitude',
            'distance_from_office', 'is_within_geofence',
            'minutes_late', 'notes'
        ]
        read_only_fields = ['id', 'user', 'minutes_late', 'distance_from_office', 'is_within_geofence']


class CheckInRequestSerializer(serializers.Serializer):
    """Sérialiseur pour la requête de pointage"""
    qr_token = serializers.CharField()
    company_id = serializers.UUIDField()
    pin_code = serializers.CharField(required=False, allow_blank=True)
    employee_id = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    device_info = serializers.CharField(required=False, allow_blank=True)


class DailyAttendanceSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    department_name = serializers.CharField(source='user.department.name', read_only=True)
    department_color = serializers.CharField(source='user.department.color', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DailyAttendance
        fields = [
            'id', 'user', 'user_name', 'user_avatar', 'department_name', 'department_color',
            'date', 'check_in_time', 'check_out_time', 'total_hours',
            'break_duration_minutes', 'minutes_late', 'overtime_hours',
            'status', 'status_display', 'notes'
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_count = serializers.IntegerField(read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'user', 'user_name', 'leave_type', 'leave_type_display',
            'start_date', 'end_date', 'days_count', 'reason', 'document',
            'status', 'status_display', 'reviewed_by', 'reviewed_by_name',
            'review_comment', 'reviewed_at', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'reviewed_by', 'reviewed_at', 'created_at']


class DisciplinaryActionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.full_name', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = DisciplinaryAction
        fields = [
            'id', 'user', 'user_name', 'issued_by', 'issued_by_name',
            'action_type', 'action_type_display', 'severity', 'severity_display',
            'reason', 'description', 'is_acknowledged', 'acknowledged_at', 'created_at'
        ]
        read_only_fields = ['id', 'issued_by', 'created_at']
