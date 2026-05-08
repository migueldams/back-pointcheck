from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    get_current_qr, public_check_in,
    AttendanceRecordViewSet, DailyAttendanceViewSet,
    LeaveRequestViewSet, DisciplinaryActionViewSet
)

router = DefaultRouter()
router.register('records', AttendanceRecordViewSet, basename='record')
router.register('daily', DailyAttendanceViewSet, basename='daily')
router.register('leaves', LeaveRequestViewSet, basename='leave')
router.register('disciplinary', DisciplinaryActionViewSet, basename='disciplinary')

urlpatterns = [
    path('qr/current/', get_current_qr, name='current_qr'),
    path('check-in/', public_check_in, name='public_check_in'),
    path('', include(router.urls)),
]
