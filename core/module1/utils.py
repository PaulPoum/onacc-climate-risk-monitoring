# core/module1/utils.py
"""
Utilitaires communs pour Module 1
"""
from typing import Tuple, Dict
import numpy as np
from math import radians, sin, cos, sqrt, atan2

def calculate_risk_level(
    value: float,
    thresholds: Dict[str, float]
) -> str:
    """
    Calcule le niveau de risque basé sur des seuils
    
    Args:
        value: Valeur à évaluer
        thresholds: {'critical': X, 'high': Y, 'moderate': Z}
    
    Returns:
        'critical' | 'high' | 'moderate' | 'low'
    
    Example:
        >>> thresholds = {'critical': 100, 'high': 70, 'moderate': 50}
        >>> calculate_risk_level(120, thresholds)
        'critical'
    """
    
    if value >= thresholds.get('critical', float('inf')):
        return 'critical'
    elif value >= thresholds.get('high', float('inf')):
        return 'high'
    elif value >= thresholds.get('moderate', float('inf')):
        return 'moderate'
    else:
        return 'low'

def format_coordinates(lat: float, lon: float, precision: int = 4) -> str:
    """
    Formate les coordonnées pour affichage
    
    Args:
        lat: Latitude
        lon: Longitude
        precision: Nombre de décimales
    
    Returns:
        String formaté "X.XXXX°N, Y.YYYY°E"
    
    Example:
        >>> format_coordinates(3.8480, 11.5021)
        '3.8480°N, 11.5021°E'
    """
    
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'O'
    
    return f"{abs(lat):.{precision}f}°{lat_dir}, {abs(lon):.{precision}f}°{lon_dir}"

def get_bbox_from_point(
    lat: float,
    lon: float,
    radius_km: float = 50
) -> Tuple[float, float, float, float]:
    """
    Calcule une bounding box autour d'un point
    
    Args:
        lat: Latitude centre
        lon: Longitude centre
        radius_km: Rayon en km
    
    Returns:
        (min_lon, min_lat, max_lon, max_lat)
    
    Example:
        >>> bbox = get_bbox_from_point(3.8480, 11.5021, 50)
        >>> len(bbox)
        4
    """
    
    # Approximation: 1 degré lat ≈ 111 km
    # 1 degré lon ≈ 111 km * cos(lat)
    
    lat_offset = radius_km / 111.0
    lon_offset = radius_km / (111.0 * np.cos(np.radians(lat)))
    
    return (
        lon - lon_offset,  # min_lon
        lat - lat_offset,  # min_lat
        lon + lon_offset,  # max_lon
        lat + lat_offset   # max_lat
    )

def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calcule la distance haversine entre deux points (great-circle distance)
    
    Args:
        lat1, lon1: Coordonnées point 1
        lat2, lon2: Coordonnées point 2
    
    Returns:
        Distance en km
    
    Example:
        >>> # Distance Yaoundé - Douala (≈250 km)
        >>> d = haversine_distance(3.8480, 11.5021, 4.0511, 9.7679)
        >>> 240 < d < 260
        True
    """
    
    R = 6371  # Rayon Terre en km
    
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    
    a = (sin(dlat/2)**2 + 
         cos(radians(lat1)) * cos(radians(lat2)) * 
         sin(dlon/2)**2)
    
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def get_risk_color(risk_level: str) -> str:
    """
    Retourne la couleur associée au niveau de risque
    
    Args:
        risk_level: 'critical' | 'high' | 'moderate' | 'low'
    
    Returns:
        Code couleur hexadécimal
    """
    
    colors = {
        'critical': '#f44336',  # Rouge
        'high': '#ff9800',      # Orange
        'moderate': '#ffc107',  # Jaune
        'low': '#4caf50'        # Vert
    }
    return colors.get(risk_level, '#4caf50')

def get_risk_label(risk_level: str, language: str = 'fr') -> str:
    """
    Retourne le label du niveau de risque dans la langue spécifiée
    
    Args:
        risk_level: 'critical' | 'high' | 'moderate' | 'low'
        language: 'fr' | 'en'
    
    Returns:
        Label traduit
    """
    
    labels = {
        'fr': {
            'critical': 'CRITIQUE',
            'high': 'ÉLEVÉ',
            'moderate': 'MODÉRÉ',
            'low': 'FAIBLE'
        },
        'en': {
            'critical': 'CRITICAL',
            'high': 'HIGH',
            'moderate': 'MODERATE',
            'low': 'LOW'
        }
    }
    
    return labels.get(language, labels['fr']).get(risk_level, 'UNKNOWN')

def calculate_bbox_area(bbox: Tuple[float, float, float, float]) -> float:
    """
    Calcule la surface approximative d'une bounding box
    
    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
    
    Returns:
        Surface en km²
    """
    
    min_lon, min_lat, max_lon, max_lat = bbox
    
    # Largeur et hauteur approximatives
    width_km = haversine_distance(min_lat, min_lon, min_lat, max_lon)
    height_km = haversine_distance(min_lat, min_lon, max_lat, min_lon)
    
    return width_km * height_km

def format_large_number(value: float, unit: str = '') -> str:
    """
    Formate un grand nombre pour affichage lisible
    
    Args:
        value: Valeur à formater
        unit: Unité optionnelle
    
    Returns:
        String formaté
    
    Example:
        >>> format_large_number(1500000, 'm²')
        '1.5M m²'
    """
    
    if value >= 1_000_000_000:
        return f"{value/1_000_000_000:.1f}G{unit}"
    elif value >= 1_000_000:
        return f"{value/1_000_000:.1f}M{unit}"
    elif value >= 1_000:
        return f"{value/1_000:.1f}k{unit}"
    else:
        return f"{value:.1f}{unit}"