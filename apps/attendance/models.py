"""
Modèles pour le pointage : Sessions, Pointages, Absences
"""
from django.db import models
from django.utils import timezone
from apps.accounts.models import User, Company
import uuid


class AttendanceRecord(models.Model):
    """Enregistrement de pointage (entrée ou sortie)"""
    
    class CheckType(models.TextChoices):
        CHECK_IN = 'check_in', 'Arrivée'
        CHECK_OUT = 'check_out', 'Sortie'
        BREAK_START = 'break_start', 'Début de pause'
        BREAK_END = 'break_end', 'Fin de pause'
    
    class Status(models.TextChoices):
        ON_TIME = 'on_time', 'À l\'heure'
        LATE = 'late', 'En retard'
        EARLY_LEAVE = 'early_leave', 'Départ anticipé'
        OVERTIME = 'overtime', 'Heures supp.'
        NORMAL = 'normal', 'Normal'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='attendance_records')
    
    check_type = models.CharField(max_length=20, choices=CheckType.choices)
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NORMAL)
    
    # Géolocalisation au moment du pointage
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    distance_from_office = models.FloatField(null=True, blank=True, help_text="Distance en mètres")
    is_within_geofence = models.BooleanField(default=True)
    
    # Métadonnées du device
    device_info = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Validation
    qr_token_used = models.CharField(max_length=128, blank=True)
    minutes_late = models.IntegerField(default=0, help_text="Minutes de retard ou d'avance")
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['company', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} - {self.get_check_type_display()} - {self.timestamp:%d/%m/%Y %H:%M}"


class DailyAttendance(models.Model):
    """Récapitulatif journalier de présence"""
    
    class DayStatus(models.TextChoices):
        PRESENT = 'present', 'Présent'
        ABSENT = 'absent', 'Absent'
        LATE = 'late', 'En retard'
        HALF_DAY = 'half_day', 'Demi-journée'
        ON_LEAVE = 'on_leave', 'En congé'
        HOLIDAY = 'holiday', 'Jour férié'
        WEEKEND = 'weekend', 'Weekend'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_attendances')
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField()
    
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    
    total_hours = models.FloatField(default=0)
    break_duration_minutes = models.IntegerField(default=0)
    minutes_late = models.IntegerField(default=0)
    overtime_hours = models.FloatField(default=0)
    
    status = models.CharField(max_length=20, choices=DayStatus.choices, default=DayStatus.ABSENT)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']
        indexes = [models.Index(fields=['user', '-date']), models.Index(fields=['company', '-date'])]
    
    def __str__(self):
        return f"{self.user.full_name} - {self.date} - {self.get_status_display()}"


class LeaveRequest(models.Model):
    """Demande de congé / absence justifiée"""
    
    class LeaveType(models.TextChoices):
        VACATION = 'vacation', 'Congés payés'
        SICK = 'sick', 'Maladie'
        PERSONAL = 'personal', 'Personnel'
        UNPAID = 'unpaid', 'Sans solde'
        OTHER = 'other', 'Autre'
    
    class LeaveStatus(models.TextChoices):
        PENDING = 'pending', 'En attente'
        APPROVED = 'approved', 'Approuvé'
        REJECTED = 'rejected', 'Refusé'
        CANCELLED = 'cancelled', 'Annulé'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    document = models.FileField(upload_to='leaves/documents/', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_leaves'
    )
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    @property
    def days_count(self):
        return (self.end_date - self.start_date).days + 1
    
    def __str__(self):
        return f"{self.user.full_name} - {self.leave_type} - {self.start_date}"


class DisciplinaryAction(models.Model):
    """Action disciplinaire / avertissement"""
    
    class ActionType(models.TextChoices):
        WARNING = 'warning', 'Avertissement'
        NOTICE = 'notice', 'Notification'
        SUSPENSION = 'suspension', 'Suspension'
        OTHER = 'other', 'Autre'
    
    class Severity(models.TextChoices):
        LOW = 'low', 'Faible'
        MEDIUM = 'medium', 'Moyen'
        HIGH = 'high', 'Élevé'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disciplinary_actions')
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_actions')
    
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.LOW)
    reason = models.TextField()
    description = models.TextField(blank=True)
    
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.get_action_type_display()}"
