from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, Department


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    search_fields = ['name', 'slug']
    list_filter = ['is_active']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'created_at']
    list_filter = ['company']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'full_name', 'email', 'role', 'company', 'department', 'is_active_employee']
    list_filter = ['role', 'company', 'department', 'is_active_employee']
    fieldsets = UserAdmin.fieldsets + (
        ('PointCheck', {'fields': ('company', 'department', 'role', 'employee_id', 
                                    'pin_code', 'phone', 'avatar', 'contract_type',
                                    'custom_start_time', 'custom_end_time',
                                    'hire_date', 'is_active_employee')}),
    )
