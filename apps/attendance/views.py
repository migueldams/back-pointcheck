"""Vues API pour le pointage et les QR codes"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta, date
from io import BytesIO
import qrcode
import base64
from corsheaders.defaults import default_headers

from apps.accounts.models import Company, User
from .models import AttendanceRecord, DailyAttendance, LeaveRequest, DisciplinaryAction
from .serializers import (
    AttendanceRecordSerializer, CheckInRequestSerializer,
    DailyAttendanceSerializer, LeaveRequestSerializer,
    DisciplinaryActionSerializer
)
from .utils import (
    generate_qr_token, verify_qr_token,
    is_within_geofence, calculate_minutes_late
)


class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'manager']


# ============ QR CODE ENDPOINTS ============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_qr(request):
    """
    Retourne le QR code dynamique actuel pour l'entreprise.
    Le QR contient un token qui change toutes les 60 secondes.
    """
    company = request.user.company
    if not company:
        return Response({'detail': 'Aucune entreprise associée'}, status=400)
    
    token, time_window = generate_qr_token(str(company.id), company.qr_secret_key)
    
    # URL que les employés scannent
    base_url = request.build_absolute_uri('/').rstrip('/')
    # Le frontend gère l'URL de pointage
    frontend_url = request.headers.get('X-Frontend-Url', 'http://localhost:5173')
    qr_data = f"{frontend_url}/check-in?company={company.id}&token={token}"
    
    # Génération de l'image QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    
    import time
    seconds_remaining = 60 - (int(time.time()) % 60)
    
    return Response({
        'qr_image': f"data:image/png;base64,{img_base64}",
        'qr_data': qr_data,
        'token': token,
        'company_id': str(company.id),
        'company_name': company.name,
        'expires_in_seconds': seconds_remaining,
        'validity_seconds': 60,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def public_check_in(request):
    """
    Endpoint public de pointage par QR code.
    L'employé n'a pas besoin d'être connecté à une session.
    Il s'identifie via son employee_id + pin_code.
    """
    serializer = CheckInRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    
    # Vérifier l'entreprise
    try:
        company = Company.objects.get(id=data['company_id'])
    except Company.DoesNotExist:
        return Response({'detail': 'Entreprise introuvable'}, status=404)
    
    # Vérifier le token QR
    if not verify_qr_token(data['qr_token'], str(company.id), company.qr_secret_key):
        return Response({
            'detail': 'QR code expiré ou invalide. Demandez à votre administrateur le QR code à jour.',
            'code': 'INVALID_QR'
        }, status=400)
    
    # Identifier l'employé
    employee_id = data.get('employee_id', '').strip()
    pin_code = data.get('pin_code', '').strip()
    
    if not employee_id:
        return Response({'detail': 'Matricule requis', 'code': 'MISSING_EMPLOYEE_ID'}, status=400)
    
    try:
        user = User.objects.get(
            company=company,
            employee_id=employee_id,
            is_active_employee=True
        )
    except User.DoesNotExist:
        return Response({
            'detail': 'Matricule non trouvé ou employé inactif',
            'code': 'EMPLOYEE_NOT_FOUND'
        }, status=404)
    
    # Vérifier le PIN si configuré
    if user.pin_code and user.pin_code != pin_code:
        return Response({'detail': 'Code PIN incorrect', 'code': 'INVALID_PIN'}, status=403)
    
    # Vérifier le geofencing
    user_lat = data.get('latitude')
    user_lon = data.get('longitude')
    within_geofence, distance = is_within_geofence(
        user_lat, user_lon,
        company.latitude, company.longitude,
        company.geofence_radius
    )
    
    if not within_geofence and company.latitude and company.longitude:
        return Response({
            'detail': f'Vous êtes à {int(distance)}m du bureau (limite: {company.geofence_radius}m). Pointage refusé.',
            'code': 'OUT_OF_GEOFENCE',
            'distance': distance,
        }, status=403)
    
    # Déterminer le type de pointage (entrée ou sortie)
    today = timezone.now().date()
    today_records = AttendanceRecord.objects.filter(
        user=user, timestamp__date=today
    ).order_by('-timestamp')
    
    if not today_records.exists() or today_records.first().check_type == 'check_out':
        check_type = 'check_in'
    else:
        last = today_records.first()
        if last.check_type == 'check_in':
            check_type = 'check_out'
        elif last.check_type == 'break_start':
            check_type = 'break_end'
        elif last.check_type == 'break_end':
            check_type = 'check_out'
        else:
            check_type = 'check_in'
    
    # Calculer le retard si c'est une arrivée
    minutes_late = 0
    record_status = AttendanceRecord.Status.NORMAL
    
    now = timezone.now()
    if check_type == 'check_in' and user.work_start_time:
        minutes_late = calculate_minutes_late(
            now, user.work_start_time, company.late_tolerance_minutes
        )
        if minutes_late > 0:
            record_status = AttendanceRecord.Status.LATE
        else:
            record_status = AttendanceRecord.Status.ON_TIME
    
    # Créer l'enregistrement
    record = AttendanceRecord.objects.create(
        user=user,
        company=company,
        check_type=check_type,
        timestamp=now,
        status=record_status,
        latitude=user_lat,
        longitude=user_lon,
        distance_from_office=distance,
        is_within_geofence=within_geofence,
        device_info=data.get('device_info', '')[:255],
        ip_address=request.META.get('REMOTE_ADDR'),
        qr_token_used=data['qr_token'][:128],
        minutes_late=minutes_late,
    )
    
    # Mettre à jour le récap journalier
    update_daily_attendance(user, today, company)
    
    return Response({
        'success': True,
        'message': f'Pointage enregistré : {record.get_check_type_display()}',
        'record': AttendanceRecordSerializer(record).data,
        'user_name': user.full_name,
        'check_type': check_type,
        'check_type_display': record.get_check_type_display(),
        'timestamp': record.timestamp,
        'minutes_late': minutes_late,
        'status': record_status,
    })


def update_daily_attendance(user, day, company):
    """Met à jour le récapitulatif journalier"""
    records = AttendanceRecord.objects.filter(
        user=user, timestamp__date=day
    ).order_by('timestamp')
    
    if not records.exists():
        return
    
    daily, _ = DailyAttendance.objects.get_or_create(
        user=user, date=day, defaults={'company': company}
    )
    
    check_ins = records.filter(check_type='check_in')
    check_outs = records.filter(check_type='check_out')
    
    if check_ins.exists():
        daily.check_in_time = check_ins.first().timestamp
        daily.minutes_late = check_ins.first().minutes_late
    
    if check_outs.exists():
        daily.check_out_time = check_outs.last().timestamp
    
    if daily.check_in_time and daily.check_out_time:
        delta = daily.check_out_time - daily.check_in_time
        daily.total_hours = round(delta.total_seconds() / 3600, 2)
    
    # Statut du jour
    if daily.minutes_late > company.late_tolerance_minutes:
        daily.status = DailyAttendance.DayStatus.LATE
    elif daily.check_in_time:
        daily.status = DailyAttendance.DayStatus.PRESENT
    
    daily.save()


# ============ VIEWSETS ============

class AttendanceRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['user', 'check_type', 'status']
    
    def get_queryset(self):
        user = self.request.user
        if not user.company:
            return AttendanceRecord.objects.none()
        
        qs = AttendanceRecord.objects.filter(company=user.company)
        
        # Les employés ne voient que leurs propres pointages
        if user.role == 'employee':
            qs = qs.filter(user=user)
        elif user.role == 'manager':
            qs = qs.filter(user__department=user.department)
        
        # Filtres date
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        
        return qs.select_related('user', 'user__department').order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def today_live(self, request):
        """Pointages d'aujourd'hui en temps réel"""
        today = timezone.now().date()
        qs = self.get_queryset().filter(timestamp__date=today)[:50]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_history(self, request):
        """Historique de l'utilisateur connecté"""
        qs = AttendanceRecord.objects.filter(user=request.user).order_by('-timestamp')[:100]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DailyAttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyAttendanceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['user', 'status', 'date']
    
    def get_queryset(self):
        user = self.request.user
        if not user.company:
            return DailyAttendance.objects.none()
        
        qs = DailyAttendance.objects.filter(company=user.company)
        if user.role == 'employee':
            qs = qs.filter(user=user)
        elif user.role == 'manager':
            qs = qs.filter(user__department=user.department)
        
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        
        return qs.select_related('user', 'user__department').order_by('-date')


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'leave_type', 'user']
    
    def get_queryset(self):
        user = self.request.user
        if not user.company:
            return LeaveRequest.objects.none()
        
        qs = LeaveRequest.objects.filter(company=user.company)
        if user.role == 'employee':
            qs = qs.filter(user=user)
        elif user.role == 'manager':
            qs = qs.filter(user__department=user.department)
        
        return qs.select_related('user', 'reviewed_by').order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, company=self.request.user.company)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def approve(self, request, pk=None):
        leave = self.get_object()
        leave.status = LeaveRequest.LeaveStatus.APPROVED
        leave.reviewed_by = request.user
        leave.reviewed_at = timezone.now()
        leave.review_comment = request.data.get('comment', '')
        leave.save()
        return Response(self.get_serializer(leave).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def reject(self, request, pk=None):
        leave = self.get_object()
        leave.status = LeaveRequest.LeaveStatus.REJECTED
        leave.reviewed_by = request.user
        leave.reviewed_at = timezone.now()
        leave.review_comment = request.data.get('comment', '')
        leave.save()
        return Response(self.get_serializer(leave).data)


class DisciplinaryActionViewSet(viewsets.ModelViewSet):
    serializer_class = DisciplinaryActionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['action_type', 'severity', 'user']
    
    def get_queryset(self):
        user = self.request.user
        if not user.company:
            return DisciplinaryAction.objects.none()
        
        qs = DisciplinaryAction.objects.filter(company=user.company)
        if user.role == 'employee':
            qs = qs.filter(user=user)
        elif user.role == 'manager':
            qs = qs.filter(user__department=user.department)
        
        return qs.select_related('user', 'issued_by').order_by('-created_at')
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user, company=self.request.user.company)
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        action_obj = self.get_object()
        if action_obj.user != request.user:
            return Response({'detail': 'Non autorisé'}, status=403)
        action_obj.is_acknowledged = True
        action_obj.acknowledged_at = timezone.now()
        action_obj.save()
        return Response(self.get_serializer(action_obj).data)
