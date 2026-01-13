# core/module2/utils.py
"""
Module 2 - Utilitaires
Fonctions helpers pour la cartographie et l'analyse spatiale
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
from datetime import datetime

# ========================================
# COLOR SCALES
# ========================================

def create_risk_color_scale(risk_type: str = 'flood') -> Dict[str, str]:
    """
    Crée une échelle de couleurs pour les niveaux de risque
    
    Args:
        risk_type: Type de risque ('flood', 'drought', 'heat', 'erosion')
    
    Returns:
        Dictionnaire {niveau: couleur_hex}
    """
    color_scales = {
        'flood': {
            'low': '#4caf50',      # Vert
            'moderate': '#ffc107', # Jaune
            'high': '#ff9800',     # Orange
            'critical': '#f44336', # Rouge
            'extreme': '#8b0000'   # Rouge foncé
        },
        'drought': {
            'normal': '#4caf50',        # Vert
            'abnormally_dry': '#ffc107', # Jaune
            'moderate': '#ff9800',      # Orange
            'severe': '#f44336',        # Rouge
            'extreme': '#8b0000',       # Rouge foncé
            'exceptional': '#4a0404'    # Bordeaux
        },
        'heat': {
            'normal': '#81c784',    # Vert clair
            'caution': '#ffeb3b',   # Jaune
            'extreme_caution': '#ff9800', # Orange
            'danger': '#f44336',    # Rouge
            'extreme_danger': '#8b0000' # Rouge foncé
        },
        'erosion': {
            'low': '#8bc34a',       # Vert olive
            'moderate': '#ffeb3b',  # Jaune
            'high': '#ff9800',      # Orange
            'severe': '#f44336'     # Rouge
        }
    }
    
    return color_scales.get(risk_type, color_scales['flood'])


def get_risk_level_label(level: str, risk_type: str = 'flood', lang: str = 'fr') -> str:
    """
    Retourne le label correspondant au niveau de risque
    
    Args:
        level: Niveau de risque
        risk_type: Type de risque
        lang: Langue ('fr' ou 'en')
    
    Returns:
        Label traduit
    """
    labels_fr = {
        'flood': {
            'low': 'Faible',
            'moderate': 'Modéré',
            'high': 'Élevé',
            'critical': 'Critique',
            'extreme': 'Extrême'
        },
        'drought': {
            'normal': 'Normal',
            'abnormally_dry': 'Anormalement sec',
            'moderate': 'Modéré',
            'severe': 'Sévère',
            'extreme': 'Extrême',
            'exceptional': 'Exceptionnel'
        },
        'heat': {
            'normal': 'Normal',
            'caution': 'Attention',
            'extreme_caution': 'Attention extrême',
            'danger': 'Danger',
            'extreme_danger': 'Danger extrême'
        }
    }
    
    labels_en = {
        'flood': {
            'low': 'Low',
            'moderate': 'Moderate',
            'high': 'High',
            'critical': 'Critical',
            'extreme': 'Extreme'
        },
        'drought': {
            'normal': 'Normal',
            'abnormally_dry': 'Abnormally Dry',
            'moderate': 'Moderate',
            'severe': 'Severe',
            'extreme': 'Extreme',
            'exceptional': 'Exceptional'
        }
    }
    
    labels = labels_fr if lang == 'fr' else labels_en
    return labels.get(risk_type, {}).get(level, level.title())


# ========================================
# FORMATTING
# ========================================

def format_area(area_km2: float) -> str:
    """
    Formate une surface en km² avec unité appropriée
    
    Args:
        area_km2: Surface en km²
    
    Returns:
        Chaîne formatée avec unité
    """
    if area_km2 < 1:
        # Convertir en hectares
        return f"{area_km2 * 100:.1f} ha"
    elif area_km2 < 1000:
        return f"{area_km2:.2f} km²"
    else:
        return f"{area_km2:,.0f} km²"


def format_coordinates(lat: float, lon: float, precision: int = 4) -> str:
    """
    Formate des coordonnées GPS
    
    Args:
        lat: Latitude
        lon: Longitude
        precision: Nombre de décimales
    
    Returns:
        Coordonnées formatées
    """
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    
    return f"{abs(lat):.{precision}f}°{lat_dir}, {abs(lon):.{precision}f}°{lon_dir}"


def format_population(pop: int) -> str:
    """
    Formate un nombre d'habitants
    
    Args:
        pop: Population
    
    Returns:
        Chaîne formatée
    """
    if pop < 1000:
        return str(pop)
    elif pop < 1_000_000:
        return f"{pop / 1000:.1f}k"
    else:
        return f"{pop / 1_000_000:.2f}M"


# ========================================
# SPATIAL CALCULATIONS
# ========================================

def calculate_zone_statistics(values: np.ndarray, area_km2: float) -> Dict:
    """
    Calcule des statistiques pour une zone
    
    Args:
        values: Valeurs (précipitations, températures, etc.)
        area_km2: Surface de la zone
    
    Returns:
        Dictionnaire de statistiques
    """
    if len(values) == 0:
        return {
            'mean': 0,
            'median': 0,
            'std': 0,
            'min': 0,
            'max': 0,
            'area_km2': area_km2
        }
    
    return {
        'mean': float(np.mean(values)),
        'median': float(np.median(values)),
        'std': float(np.std(values)),
        'min': float(np.min(values)),
        'max': float(np.max(values)),
        'p25': float(np.percentile(values, 25)),
        'p75': float(np.percentile(values, 75)),
        'area_km2': area_km2
    }


def get_bounding_box(lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
    """
    Calcule une bounding box autour d'un point
    
    Args:
        lat: Latitude centrale
        lon: Longitude centrale
        radius_km: Rayon en km
    
    Returns:
        (min_lon, min_lat, max_lon, max_lat)
    """
    # Approximation simple : 1° ≈ 111 km
    delta = radius_km / 111.0
    
    return (
        lon - delta,  # min_lon
        lat - delta,  # min_lat
        lon + delta,  # max_lon
        lat + delta   # max_lat
    )


def point_in_bbox(lat: float, lon: float, bbox: Tuple[float, float, float, float]) -> bool:
    """
    Vérifie si un point est dans une bounding box
    
    Args:
        lat: Latitude du point
        lon: Longitude du point
        bbox: (min_lon, min_lat, max_lon, max_lat)
    
    Returns:
        True si le point est dans la bbox
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


# ========================================
# RISK CLASSIFICATION
# ========================================

def classify_flood_risk(
    precipitation_mm: float,
    discharge_m3s: Optional[float] = None,
    water_level_m: Optional[float] = None
) -> str:
    """
    Classifie le risque d'inondation
    
    Args:
        precipitation_mm: Précipitations en mm
        discharge_m3s: Débit optionnel en m³/s
        water_level_m: Niveau d'eau optionnel en m
    
    Returns:
        Niveau de risque
    """
    # Classification basée sur les précipitations
    if precipitation_mm >= 100:
        base_risk = 'extreme'
    elif precipitation_mm >= 70:
        base_risk = 'critical'
    elif precipitation_mm >= 50:
        base_risk = 'high'
    elif precipitation_mm >= 30:
        base_risk = 'moderate'
    else:
        base_risk = 'low'
    
    # Ajustement avec débit si disponible
    if discharge_m3s is not None:
        if discharge_m3s >= 500:  # Seuil à adapter selon bassin
            return 'extreme'
        elif discharge_m3s >= 300:
            return max(base_risk, 'critical', key=lambda x: ['low', 'moderate', 'high', 'critical', 'extreme'].index(x))
    
    return base_risk


def classify_drought_severity(
    consecutive_dry_days: int,
    precipitation_deficit_pct: float,
    spi: Optional[float] = None
) -> str:
    """
    Classifie la sévérité de la sécheresse
    
    Args:
        consecutive_dry_days: Nombre de jours secs consécutifs
        precipitation_deficit_pct: Déficit pluviométrique en %
        spi: Standardized Precipitation Index (optionnel)
    
    Returns:
        Sévérité de la sécheresse
    """
    # Classification basée sur jours secs
    if consecutive_dry_days >= 60:
        base_severity = 'exceptional'
    elif consecutive_dry_days >= 45:
        base_severity = 'extreme'
    elif consecutive_dry_days >= 30:
        base_severity = 'severe'
    elif consecutive_dry_days >= 15:
        base_severity = 'moderate'
    elif consecutive_dry_days >= 7:
        base_severity = 'abnormally_dry'
    else:
        base_severity = 'normal'
    
    # Ajustement avec déficit si disponible
    if precipitation_deficit_pct >= 50:
        return 'exceptional'
    elif precipitation_deficit_pct >= 40 and base_severity in ['severe', 'extreme', 'exceptional']:
        return 'extreme'
    
    # Ajustement avec SPI si disponible
    if spi is not None:
        if spi <= -2.0:
            return 'exceptional'
        elif spi <= -1.5:
            return max(base_severity, 'extreme', key=lambda x: ['normal', 'abnormally_dry', 'moderate', 'severe', 'extreme', 'exceptional'].index(x))
    
    return base_severity


# ========================================
# TIME UTILITIES
# ========================================

def get_season(date: datetime) -> str:
    """
    Détermine la saison au Cameroun
    
    Args:
        date: Date à analyser
    
    Returns:
        Saison ('dry_season' ou 'rainy_season')
    """
    month = date.month
    
    # Saison des pluies : mai à octobre
    if 5 <= month <= 10:
        return 'rainy_season'
    else:
        return 'dry_season'


def get_season_label(season: str, lang: str = 'fr') -> str:
    """
    Retourne le label de la saison
    
    Args:
        season: Saison ('dry_season' ou 'rainy_season')
        lang: Langue
    
    Returns:
        Label traduit
    """
    labels = {
        'fr': {
            'dry_season': 'Saison sèche',
            'rainy_season': 'Saison des pluies'
        },
        'en': {
            'dry_season': 'Dry Season',
            'rainy_season': 'Rainy Season'
        }
    }
    
    return labels.get(lang, labels['fr']).get(season, season)


# ========================================
# VALIDATION
# ========================================

def validate_coordinates(lat: float, lon: float, country: str = 'CM') -> bool:
    """
    Valide que des coordonnées sont au Cameroun
    
    Args:
        lat: Latitude
        lon: Longitude
        country: Code pays (CM = Cameroun)
    
    Returns:
        True si valide
    """
    if country == 'CM':
        # Limites approximatives du Cameroun
        return (1.5 <= lat <= 13.1) and (8.3 <= lon <= 16.2)
    
    # Validation générique
    return (-90 <= lat <= 90) and (-180 <= lon <= 180)


def validate_risk_level(level: str, risk_type: str = 'flood') -> bool:
    """
    Valide un niveau de risque
    
    Args:
        level: Niveau à valider
        risk_type: Type de risque
    
    Returns:
        True si valide
    """
    valid_levels = {
        'flood': ['low', 'moderate', 'high', 'critical', 'extreme'],
        'drought': ['normal', 'abnormally_dry', 'moderate', 'severe', 'extreme', 'exceptional'],
        'heat': ['normal', 'caution', 'extreme_caution', 'danger', 'extreme_danger'],
        'erosion': ['low', 'moderate', 'high', 'severe']
    }
    
    return level in valid_levels.get(risk_type, [])


# ========================================
# MAP CREATION
# ========================================

def create_choropleth_map(
    zones_data: List[Dict],
    value_column: str,
    color_scale: Optional[str] = None,
    title: str = "Carte Choroplèthe"
) -> Dict:
    """
    Crée une configuration de carte choroplèthe
    
    Args:
        zones_data: Données des zones avec geometries
        value_column: Colonne contenant les valeurs à afficher
        color_scale: Échelle de couleurs (optionnel)
        title: Titre de la carte
    
    Returns:
        Configuration Plotly pour carte choroplèthe
    """
    import plotly.graph_objects as go
    
    if color_scale is None:
        color_scale = 'YlOrRd'
    
    # Extraire coordonnées et valeurs
    lats = []
    lons = []
    values = []
    names = []
    
    for zone in zones_data:
        if 'center_lat' in zone and 'center_lon' in zone:
            lats.append(zone['center_lat'])
            lons.append(zone['center_lon'])
            values.append(zone.get(value_column, 0))
            names.append(zone.get('name', 'Zone'))
    
    # Créer figure
    fig = go.Figure(data=go.Scattermapbox(
        lat=lats,
        lon=lons,
        mode='markers',
        marker=dict(
            size=15,
            color=values,
            colorscale=color_scale,
            showscale=True,
            colorbar=dict(title=value_column)
        ),
        text=names,
        hoverinfo='text'
    ))
    
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=np.mean(lats) if lats else 6.0, lon=np.mean(lons) if lons else 12.0),
            zoom=5
        ),
        height=600,
        title=title
    )
    
    return fig


def get_risk_color_scale(risk_type: str = 'flood') -> Dict[str, str]:
    """
    Alias pour create_risk_color_scale (compatibilité)
    """
    return create_risk_color_scale(risk_type)