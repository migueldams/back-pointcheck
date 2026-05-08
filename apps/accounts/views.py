"""Vues API pour les comptes"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User, Company, Department
from .serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateSerializer,
    CompanySerializer, DepartmentSerializer,
    CustomTokenObtainPairSerializer, RegisterCompanySerializer
)


class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'manager']


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterCompanyView(viewsets.GenericViewSet):
    """Inscription d'une nouvelle entreprise"""
    permission_classes = [AllowAny]
    serializer_class = RegisterCompanySerializer
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({
            'message': 'Entreprise créée avec succès',
            'company_id': str(result['company'].id),
            'admin_username': result['admin'].username,
        }, status=status.HTTP_201_CREATED)


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Company.objects.filter(id=self.request.user.company_id)
        return Company.objects.none()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Récupère l'entreprise de l'utilisateur connecté"""
        if not request.user.company:
            return Response({'detail': 'Aucune entreprise associée'}, status=404)
        serializer = self.get_serializer(request.user.company)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'])
    def update_me(self, request):
        """Met à jour l'entreprise de l'admin connecté"""
        if request.user.role != 'admin' or not request.user.company:
            return Response({'detail': 'Non autorisé'}, status=403)
        serializer = self.get_serializer(request.user.company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.company:
            return Department.objects.filter(company=self.request.user.company)
        return Department.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_fields = ['role', 'department', 'is_active_employee', 'contract_type']
    
    def get_queryset(self):
        user = self.request.user
        if not user.company:
            return User.objects.none()
        qs = User.objects.filter(company=user.company)
        if user.role == 'manager':
            qs = qs.filter(department=user.department)
        return qs.select_related('department', 'company').order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'retrieve':
            return UserDetailSerializer
        return UserListSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'destroy', 'update', 'partial_update']:
            return [IsAdminOrManager()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get('password', 'pointcheck123')
        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Mot de passe réinitialisé'})
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active_employee = not user.is_active_employee
        user.save()
        return Response({'is_active_employee': user.is_active_employee})
