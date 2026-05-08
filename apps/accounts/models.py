"""
Modèles pour la gestion des comptes : Entreprise, Département, Utilisateur (Employé/Manager/Admin)
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class Company(models.Model):
    """Entreprise cliente de la plateforme"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nom de l'entreprise")
    slug = models.SlugField(unique=True, max_length=100)
    logo = models.ImageField(upload_to='companies/logos/', null=True, blank=True)
    address = models.CharField(max_length=300, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    
    # Géolocalisation pour le geofencing
    latitude = models.FloatField(null=True, blank=True, help_text="Latitude du siège")
    longitude = models.FloatField(null=True, blank=True, help_text="Longitude du siège")
    geofence_radius = models.IntegerField(default=100, help_text="Rayon en mètres")
    
    # Horaires par défaut
    default_start_time = models.TimeField(default='08:00')
    default_end_time = models.TimeField(default='17:00')
    late_tolerance_minutes = models.IntegerField(default=5)
    
    # Sécurité QR
    qr_secret_key = models.CharField(max_length=64, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Entreprise"
        verbose_name_plural = "Entreprises"
    
    def save(self, *args, **kwargs):
        if not self.qr_secret_key:
            import secrets
            self.qr_secret_key = secrets.token_hex(32)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Department(models.Model):
    """Département/Service au sein de l'entreprise"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6366f1', help_text="Couleur hex")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Département"
        unique_together = ['company', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.company.name}"


class User(AbstractUser):
    """Utilisateur étendu : Admin, Manager ou Employé"""
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrateur'
        MANAGER = 'manager', 'Manager'
        EMPLOYEE = 'employee', 'Employé'
    
    class ContractType(models.TextChoices):
        FULL_TIME = 'full_time', 'Temps plein'
        PART_TIME = 'part_time', 'Temps partiel'
        INTERN = 'intern', 'Stagiaire'
        CONTRACTOR = 'contractor', 'Prestataire'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='users',
        null=True, blank=True
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='employees'
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    contract_type = models.CharField(
        max_length=20, choices=ContractType.choices, default=ContractType.FULL_TIME
    )
    
    employee_id = models.CharField(max_length=50, blank=True, help_text="Matricule")
    pin_code = models.CharField(max_length=6, blank=True, help_text="Code PIN à 4-6 chiffres")
    
    phone = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to='users/avatars/', null=True, blank=True)
    
    # Horaires personnalisés (override entreprise)
    custom_start_time = models.TimeField(null=True, blank=True)
    custom_end_time = models.TimeField(null=True, blank=True)
    
    hire_date = models.DateField(null=True, blank=True)
    is_active_employee = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def work_start_time(self):
        return self.custom_start_time or (self.company.default_start_time if self.company else None)
    
    @property
    def work_end_time(self):
        return self.custom_end_time or (self.company.default_end_time if self.company else None)
    
    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"
