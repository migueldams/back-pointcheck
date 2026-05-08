from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomTokenObtainPairView, RegisterCompanyView,
    CompanyViewSet, DepartmentViewSet, UserViewSet
)

router = DefaultRouter()
router.register('companies', CompanyViewSet, basename='company')
router.register('departments', DepartmentViewSet, basename='department')
router.register('users', UserViewSet, basename='user')
router.register('register', RegisterCompanyView, basename='register')

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('', include(router.urls)),
]
