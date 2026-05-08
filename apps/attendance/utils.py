"""
Utilitaires pour le pointage : QR codes dynamiques, géofencing, calculs
"""
import hmac
import hashlib
import time
import math
from django.conf import settings


def generate_qr_token(company_id, secret_key, validity_seconds=None):
    """
    Génère un token de QR code dynamique basé sur le temps (TOTP-like).
    Le token change toutes les X secondes (configurable).
    """
    if validity_seconds is None:
        validity_seconds = settings.QR_TOKEN_VALIDITY_SECONDS
    
    time_window = int(time.time() // validity_seconds)
    message = f"{company_id}:{time_window}".encode()
    secret = secret_key.encode()
    
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return signature[:32], time_window


def verify_qr_token(token, company_id, secret_key, validity_seconds=None):
    """
    Vérifie un token QR. Accepte le token de la fenêtre actuelle et la précédente
    (pour gérer les latences réseau).
    """
    if validity_seconds is None:
        validity_seconds = settings.QR_TOKEN_VALIDITY_SECONDS
    
    current_window = int(time.time() // validity_seconds)
    
    for window_offset in [0, -1]:  # Fenêtre courante et précédente
        time_window = current_window + window_offset
        message = f"{company_id}:{time_window}".encode()
        secret = secret_key.encode()
        expected = hmac.new(secret, message, hashlib.sha256).hexdigest()[:32]
        if hmac.compare_digest(token, expected):
            return True
    return False


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcule la distance entre 2 points GPS en mètres (formule de Haversine).
    """
    if None in (lat1, lon1, lat2, lon2):
        return None
    
    R = 6371000  # Rayon Terre en mètres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def is_within_geofence(user_lat, user_lon, company_lat, company_lon, radius_meters):
    """Vérifie si l'utilisateur est dans le périmètre autorisé"""
    if None in (user_lat, user_lon, company_lat, company_lon):
        return True, None  # Pas de geofence configuré
    distance = haversine_distance(user_lat, user_lon, company_lat, company_lon)
    return distance <= radius_meters, distance


def calculate_minutes_late(check_in_time, expected_start_time, tolerance=5):
    """Calcule les minutes de retard par rapport à l'heure prévue"""
    from datetime import datetime, timedelta
    
    expected_dt = datetime.combine(check_in_time.date(), expected_start_time)
    if hasattr(check_in_time, 'tzinfo') and check_in_time.tzinfo:
        from django.utils import timezone
        expected_dt = timezone.make_aware(expected_dt, check_in_time.tzinfo)
    
    diff = (check_in_time - expected_dt).total_seconds() / 60
    if diff > tolerance:
        return int(diff)
    return 0
