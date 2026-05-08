"""Serializers pour les comptes"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from .models import User, Company, Department


class CompanySerializer(serializers.ModelSerializer):
    employees_count = serializers.SerializerMethodField()
    departments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'slug', 'logo', 'address', 'phone', 'email',
            'latitude', 'longitude', 'geofence_radius',
            'default_start_time', 'default_end_time', 'late_tolerance_minutes',
            'is_active', 'created_at', 'employees_count', 'departments_count'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_employees_count(self, obj):
        return obj.users.filter(role='employee', is_active_employee=True).count()
    
    def get_departments_count(self, obj):
        return obj.departments.count()


class DepartmentSerializer(serializers.ModelSerializer):
    employees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = ['id', 'company', 'name', 'description', 'color', 'created_at', 'employees_count']
        read_only_fields = ['id', 'created_at']
    
    def get_employees_count(self, obj):
        return obj.employees.filter(is_active_employee=True).count()


class UserListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_color = serializers.CharField(source='department.color', read_only=True)
    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'employee_id', 'phone', 'avatar',
            'department', 'department_name', 'department_color',
            'contract_type', 'hire_date', 'is_active_employee',
            'custom_start_time', 'custom_end_time', 'created_at'
        ]


class UserDetailSerializer(UserListSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta(UserListSerializer.Meta):
        fields = UserListSerializer.Meta.fields + ['company', 'company_name', 'pin_code']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'employee_id', 'phone', 'department', 'contract_type',
            'pin_code', 'hire_date', 'custom_start_time', 'custom_end_time'
        ]
    
    def create(self, validated_data):
        password = validated_data.pop('password', None) or 'pointcheck123'
        user = User(**validated_data)
        user.set_password(password)
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.company:
            user.company = request.user.company
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT personnalisé incluant les infos utilisateur"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['full_name'] = user.full_name
        token['company_id'] = str(user.company.id) if user.company else None
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserDetailSerializer(self.user).data
        return data


class RegisterCompanySerializer(serializers.Serializer):
    """Inscription d'une nouvelle entreprise + son admin"""
    company_name = serializers.CharField(max_length=200)
    company_slug = serializers.SlugField(max_length=100)
    admin_username = serializers.CharField(max_length=150)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True, validators=[validate_password])
    admin_first_name = serializers.CharField(max_length=100)
    admin_last_name = serializers.CharField(max_length=100)
    
    def validate_company_slug(self, value):
        if Company.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Ce slug est déjà pris.")
        return value
    
    def validate_admin_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return value
    
    def create(self, validated_data):
        company = Company.objects.create(
            name=validated_data['company_name'],
            slug=validated_data['company_slug'],
        )
        admin = User.objects.create(
            username=validated_data['admin_username'],
            email=validated_data['admin_email'],
            first_name=validated_data['admin_first_name'],
            last_name=validated_data['admin_last_name'],
            role=User.Role.ADMIN,
            company=company,
        )
        admin.set_password(validated_data['admin_password'])
        admin.save()
        return {'company': company, 'admin': admin}
