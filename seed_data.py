"""
Script pour créer des données de démonstration.
Exécuter avec : python manage.py shell < seed_data.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pointcheck.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta, date, time
import random

from apps.accounts.models import User, Company, Department
from apps.attendance.models import AttendanceRecord, DailyAttendance, LeaveRequest, DisciplinaryAction


print("🌱 Seeding de la base de données...")

# Nettoyage
User.objects.filter(is_superuser=False).delete()
Company.objects.all().delete()

# Création de l'entreprise démo
company = Company.objects.create(
    name="TechCorp Cameroun",
    slug="techcorp",
    address="Douala, Bonanjo",
    phone="+237 690 00 00 00",
    email="contact@techcorp.cm",
    latitude=4.0511,
    longitude=9.7679,
    geofence_radius=200,
    default_start_time=time(8, 0),
    default_end_time=time(17, 0),
    late_tolerance_minutes=10,
)
print(f"✅ Entreprise créée : {company.name}")

# Départements
departments = []
for name, color in [
    ("Direction", "#8b5cf6"),
    ("Développement", "#3b82f6"),
    ("Marketing", "#ec4899"),
    ("RH", "#10b981"),
    ("Finance", "#f59e0b"),
]:
    dept = Department.objects.create(company=company, name=name, color=color)
    departments.append(dept)
print(f"✅ {len(departments)} départements créés")

# Admin
admin = User.objects.create(
    username="admin",
    email="admin@techcorp.cm",
    first_name="Marie",
    last_name="Ndongo",
    role=User.Role.ADMIN,
    company=company,
    department=departments[0],
    employee_id="ADM001",
    phone="+237 690 11 11 11",
    pin_code="0000",
    hire_date=date(2020, 1, 15),
)
admin.set_password("admin123")
admin.save()
print("✅ Admin créé : admin / admin123")

# Manager
manager = User.objects.create(
    username="manager",
    email="manager@techcorp.cm",
    first_name="Paul",
    last_name="Mbarga",
    role=User.Role.MANAGER,
    company=company,
    department=departments[1],
    employee_id="MGR001",
    pin_code="1234",
    hire_date=date(2021, 3, 10),
)
manager.set_password("manager123")
manager.save()
print("✅ Manager créé : manager / manager123")

# Employés
employees_data = [
    ("Jean", "Kamga", "Développement", "EMP001"),
    ("Sophie", "Tchoumi", "Développement", "EMP002"),
    ("David", "Essomba", "Développement", "EMP003"),
    ("Aminata", "Bello", "Marketing", "EMP004"),
    ("Pierre", "Owona", "Marketing", "EMP005"),
    ("Fatima", "Issa", "RH", "EMP006"),
    ("Claude", "Nkomo", "Finance", "EMP007"),
    ("Linda", "Foka", "Finance", "EMP008"),
    ("Roger", "Atangana", "Développement", "EMP009"),
    ("Carine", "Mbah", "Marketing", "EMP010"),
]

employees = []
for first, last, dept_name, emp_id in employees_data:
    dept = next((d for d in departments if d.name == dept_name), None)
    user = User.objects.create(
        username=emp_id.lower(),
        email=f"{emp_id.lower()}@techcorp.cm",
        first_name=first,
        last_name=last,
        role=User.Role.EMPLOYEE,
        company=company,
        department=dept,
        employee_id=emp_id,
        pin_code=str(random.randint(1000, 9999)),
        hire_date=date(2022, random.randint(1, 12), random.randint(1, 28)),
    )
    user.set_password("employee123")
    user.save()
    employees.append(user)

print(f"✅ {len(employees)} employés créés (mot de passe: employee123)")

# Pointages des 14 derniers jours
print("📅 Création de l'historique de pointages...")
today = timezone.now().date()
for days_back in range(14, 0, -1):
    day = today - timedelta(days=days_back)
    if day.weekday() >= 5:  # Skip weekends
        continue
    
    for emp in employees:
        # 85% de chance d'être présent
        if random.random() > 0.85:
            DailyAttendance.objects.create(
                user=emp, company=company, date=day,
                status=DailyAttendance.DayStatus.ABSENT
            )
            continue
        
        # Heure d'arrivée
        late_minutes = random.choices([0, 0, 0, 5, 15, 30], weights=[40, 20, 20, 10, 7, 3])[0]
        check_in = timezone.make_aware(
            timezone.datetime.combine(day, time(8, 0)) + timedelta(minutes=late_minutes)
        )
        
        check_in_record = AttendanceRecord.objects.create(
            user=emp, company=company,
            check_type='check_in',
            timestamp=check_in,
            status='late' if late_minutes > 10 else 'on_time',
            minutes_late=late_minutes if late_minutes > 10 else 0,
            latitude=4.0511, longitude=9.7679,
            is_within_geofence=True,
        )
        
        # Heure de sortie
        work_hours = random.uniform(7.5, 9.5)
        check_out = check_in + timedelta(hours=work_hours)
        AttendanceRecord.objects.create(
            user=emp, company=company,
            check_type='check_out',
            timestamp=check_out,
            latitude=4.0511, longitude=9.7679,
            is_within_geofence=True,
        )
        
        DailyAttendance.objects.create(
            user=emp, company=company, date=day,
            check_in_time=check_in,
            check_out_time=check_out,
            total_hours=round(work_hours, 2),
            minutes_late=late_minutes if late_minutes > 10 else 0,
            status='late' if late_minutes > 10 else 'present',
        )

print("✅ Historique créé sur 14 jours")

# Aujourd'hui : quelques pointages
print("📍 Pointages d'aujourd'hui...")
now = timezone.now()
for emp in random.sample(employees, k=7):
    minutes_late = random.choices([0, 0, 5, 20], weights=[60, 20, 15, 5])[0]
    check_in = now.replace(hour=8, minute=0, second=0) + timedelta(minutes=minutes_late)
    AttendanceRecord.objects.create(
        user=emp, company=company,
        check_type='check_in',
        timestamp=check_in,
        status='late' if minutes_late > 10 else 'on_time',
        minutes_late=minutes_late if minutes_late > 10 else 0,
        latitude=4.0511, longitude=9.7679,
        is_within_geofence=True,
    )
    DailyAttendance.objects.create(
        user=emp, company=company, date=today,
        check_in_time=check_in,
        minutes_late=minutes_late if minutes_late > 10 else 0,
        status='late' if minutes_late > 10 else 'present',
    )

# Quelques demandes de congés
print("🏖️  Demandes de congés...")
for emp in random.sample(employees, k=4):
    LeaveRequest.objects.create(
        user=emp, company=company,
        leave_type=random.choice(['vacation', 'sick', 'personal']),
        start_date=today + timedelta(days=random.randint(5, 20)),
        end_date=today + timedelta(days=random.randint(21, 30)),
        reason="Demande de congés annuels",
        status='pending',
    )

# Quelques actions disciplinaires
print("⚠️  Actions disciplinaires...")
for emp in random.sample(employees, k=2):
    DisciplinaryAction.objects.create(
        user=emp, company=company,
        issued_by=admin,
        action_type='warning',
        severity='low',
        reason="Retards répétés",
        description="Plusieurs retards constatés ce mois.",
    )

print("\n" + "=" * 60)
print("🎉 SEEDING TERMINÉ !")
print("=" * 60)
print("\n📌 COMPTES DE TEST :")
print(f"  👨‍💼 Admin    : admin / admin123")
print(f"  👔 Manager  : manager / manager123")
print(f"  👤 Employé  : emp001 / employee123 (jusqu'à emp010)")
print(f"\n📍 Entreprise : {company.name}")
print(f"📍 Slug       : {company.slug}")
print("=" * 60)
