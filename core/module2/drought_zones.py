# core/module2/drought_zones.py
"""
Module 2 - Drought Zones Analyzer
Analyse et cartographie des zones en sécheresse
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import numpy as np

from core.module2.utils import (
    classify_drought_severity,
    get_risk_level_label,
    format_area
)


class DroughtSeverity(Enum):
    """Niveaux de sévérité de la sécheresse (basé sur US Drought Monitor)"""
    NORMAL = "normal"
    ABNORMALLY_DRY = "abnormally_dry"  # D0
    MODERATE = "moderate"              # D1
    SEVERE = "severe"                  # D2
    EXTREME = "extreme"                # D3
    EXCEPTIONAL = "exceptional"        # D4


class DroughtType(Enum):
    """Types de sécheresse"""
    METEOROLOGICAL = "meteorological"  # Déficit pluviométrique
    AGRICULTURAL = "agricultural"      # Impact sur agriculture
    HYDROLOGICAL = "hydrological"      # Ressources en eau
    SOCIOECONOMIC = "socioeconomic"    # Impact socio-économique


@dataclass
class DroughtZone:
    """
    Zone en sécheresse
    
    Attributes:
        zone_id: Identifiant unique
        name: Nom de la zone
        severity: Sévérité actuelle
        drought_type: Type de sécheresse
        center_lat: Latitude centre
        center_lon: Longitude centre
        area_km2: Surface en km²
        population: Population affectée
        consecutive_dry_days: Jours secs consécutifs
        precipitation_deficit_pct: Déficit pluviométrique %
        spi: Standardized Precipitation Index
        properties: Propriétés additionnelles
    """
    zone_id: str
    name: str
    severity: DroughtSeverity
    drought_type: DroughtType
    center_lat: float
    center_lon: float
    area_km2: float
    population: Optional[int] = None
    consecutive_dry_days: int = 0
    precipitation_deficit_pct: float = 0
    spi: Optional[float] = None
    properties: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "severity": self.severity.value,
            "severity_label": get_risk_level_label(self.severity.value, 'drought'),
            "drought_type": self.drought_type.value,
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "area_km2": self.area_km2,
            "formatted_area": format_area(self.area_km2),
            "population": self.population,
            "consecutive_dry_days": self.consecutive_dry_days,
            "precipitation_deficit_pct": self.precipitation_deficit_pct,
            "spi": self.spi,
            "properties": self.properties or {}
        }


class DroughtZoneAnalyzer:
    """
    Analyseur de zones en sécheresse
    
    Fonctionnalités:
    - Identification des zones en déficit pluviométrique
    - Classification selon US Drought Monitor
    - Calcul SPI (Standardized Precipitation Index)
    - Estimation impacts agriculture et ressources en eau
    """
    
    # Zones agro-climatiques du Cameroun
    CAMEROON_DROUGHT_ZONES = {
        "extreme_nord": {
            "name": "Extrême-Nord",
            "center_lat": 11.5,
            "center_lon": 14.5,
            "area_km2": 34263,
            "population": 3900000,
            "climate_zone": "Sahélien",
            "vulnerability": "very_high"
        },
        "nord": {
            "name": "Nord",
            "center_lat": 9.5,
            "center_lon": 13.5,
            "area_km2": 66090,
            "population": 2400000,
            "climate_zone": "Soudano-sahélien",
            "vulnerability": "high"
        },
        "adamaoua": {
            "name": "Adamaoua",
            "center_lat": 7.0,
            "center_lon": 13.5,
            "area_km2": 63701,
            "population": 1200000,
            "climate_zone": "Soudanien",
            "vulnerability": "medium"
        },
        "est": {
            "name": "Est",
            "center_lat": 5.0,
            "center_lon": 14.5,
            "area_km2": 109002,
            "population": 900000,
            "climate_zone": "Équatorial",
            "vulnerability": "low"
        },
        "centre": {
            "name": "Centre",
            "center_lat": 4.5,
            "center_lon": 11.5,
            "area_km2": 68953,
            "population": 4000000,
            "climate_zone": "Équatorial",
            "vulnerability": "low"
        }
    }
    
    def __init__(self):
        self.zones: List[DroughtZone] = []
        self._load_predefined_zones()
    
    def _load_predefined_zones(self):
        """Charge les zones pré-définies"""
        for zone_id, data in self.CAMEROON_DROUGHT_ZONES.items():
            zone = DroughtZone(
                zone_id=zone_id,
                name=data["name"],
                severity=DroughtSeverity.NORMAL,  # Par défaut
                drought_type=DroughtType.METEOROLOGICAL,
                center_lat=data["center_lat"],
                center_lon=data["center_lon"],
                area_km2=data["area_km2"],
                population=data.get("population"),
                properties={
                    "climate_zone": data.get("climate_zone"),
                    "vulnerability": data.get("vulnerability")
                }
            )
            self.zones.append(zone)
    
    def analyze_zone(
        self,
        zone_id: str,
        consecutive_dry_days: int,
        precipitation_deficit_pct: float,
        spi: Optional[float] = None,
        drought_type: DroughtType = DroughtType.METEOROLOGICAL
    ) -> DroughtZone:
        """
        Analyse la sécheresse pour une zone
        
        Args:
            zone_id: ID de la zone
            consecutive_dry_days: Nombre de jours secs consécutifs
            precipitation_deficit_pct: Déficit pluviométrique en %
            spi: Standardized Precipitation Index (optionnel)
            drought_type: Type de sécheresse
        
        Returns:
            Zone avec sévérité actualisée
        """
        # Trouver la zone
        zone = self.get_zone(zone_id)
        if not zone:
            raise ValueError(f"Zone {zone_id} non trouvée")
        
        # Classifier la sévérité
        severity_str = classify_drought_severity(
            consecutive_dry_days,
            precipitation_deficit_pct,
            spi
        )
        
        # Mettre à jour
        zone.severity = DroughtSeverity(severity_str)
        zone.consecutive_dry_days = consecutive_dry_days
        zone.precipitation_deficit_pct = precipitation_deficit_pct
        zone.spi = spi
        zone.drought_type = drought_type
        
        return zone
    
    def calculate_spi(
        self,
        current_precip: float,
        historical_mean: float,
        historical_std: float
    ) -> float:
        """
        Calcule le Standardized Precipitation Index
        
        Args:
            current_precip: Précipitations actuelles
            historical_mean: Moyenne historique
            historical_std: Écart-type historique
        
        Returns:
            SPI (valeur entre -3 et +3 typiquement)
        
        Interprétation:
            SPI >= 2.0: Extrêmement humide
            1.5 <= SPI < 2.0: Très humide
            1.0 <= SPI < 1.5: Modérément humide
            -1.0 < SPI < 1.0: Normal
            -1.5 < SPI <= -1.0: Modérément sec
            -2.0 < SPI <= -1.5: Très sec
            SPI <= -2.0: Extrêmement sec
        """
        if historical_std == 0:
            return 0.0
        
        spi = (current_precip - historical_mean) / historical_std
        
        # Limiter entre -3 et +3
        return max(-3.0, min(3.0, spi))
    
    def get_zone(self, zone_id: str) -> Optional[DroughtZone]:
        """Récupère une zone par ID"""
        for zone in self.zones:
            if zone.zone_id == zone_id:
                return zone
        return None
    
    def get_zones_by_severity(self, severity: DroughtSeverity) -> List[DroughtZone]:
        """Récupère les zones d'une sévérité donnée"""
        return [z for z in self.zones if z.severity == severity]
    
    def get_critical_zones(self) -> List[DroughtZone]:
        """
        Récupère les zones critiques
        
        Returns:
            Zones avec sévérité extreme ou exceptional
        """
        return [
            z for z in self.zones
            if z.severity in [DroughtSeverity.EXTREME, DroughtSeverity.EXCEPTIONAL]
        ]
    
    def get_affected_population(
        self,
        severity_threshold: DroughtSeverity = DroughtSeverity.MODERATE
    ) -> int:
        """
        Calcule la population affectée
        
        Args:
            severity_threshold: Seuil de sévérité minimum
        
        Returns:
            Population totale affectée
        """
        severity_values = {
            DroughtSeverity.NORMAL: 0,
            DroughtSeverity.ABNORMALLY_DRY: 1,
            DroughtSeverity.MODERATE: 2,
            DroughtSeverity.SEVERE: 3,
            DroughtSeverity.EXTREME: 4,
            DroughtSeverity.EXCEPTIONAL: 5
        }
        
        threshold_value = severity_values[severity_threshold]
        
        total = 0
        for zone in self.zones:
            if severity_values[zone.severity] >= threshold_value:
                if zone.population:
                    total += zone.population
        
        return total
    
    def get_affected_area_km2(
        self,
        severity_threshold: DroughtSeverity = DroughtSeverity.MODERATE
    ) -> float:
        """Calcule la surface totale affectée"""
        severity_values = {
            DroughtSeverity.NORMAL: 0,
            DroughtSeverity.ABNORMALLY_DRY: 1,
            DroughtSeverity.MODERATE: 2,
            DroughtSeverity.SEVERE: 3,
            DroughtSeverity.EXTREME: 4,
            DroughtSeverity.EXCEPTIONAL: 5
        }
        
        threshold_value = severity_values[severity_threshold]
        
        total = 0
        for zone in self.zones:
            if severity_values[zone.severity] >= threshold_value:
                total += zone.area_km2
        
        return total
    
    def get_statistics(self) -> Dict:
        """Calcule des statistiques globales"""
        by_severity = {}
        for severity in DroughtSeverity:
            zones = self.get_zones_by_severity(severity)
            if zones:
                by_severity[severity.value] = {
                    "count": len(zones),
                    "zones": [z.name for z in zones]
                }
        
        critical_zones = self.get_critical_zones()
        
        return {
            "total_zones": len(self.zones),
            "critical_zones": len(critical_zones),
            "by_severity": by_severity,
            "affected_population": {
                "abnormally_dry_plus": self.get_affected_population(DroughtSeverity.ABNORMALLY_DRY),
                "moderate_plus": self.get_affected_population(DroughtSeverity.MODERATE),
                "severe_plus": self.get_affected_population(DroughtSeverity.SEVERE),
                "extreme_plus": self.get_affected_population(DroughtSeverity.EXTREME)
            },
            "affected_area_km2": {
                "abnormally_dry_plus": self.get_affected_area_km2(DroughtSeverity.ABNORMALLY_DRY),
                "moderate_plus": self.get_affected_area_km2(DroughtSeverity.MODERATE),
                "severe_plus": self.get_affected_area_km2(DroughtSeverity.SEVERE),
                "extreme_plus": self.get_affected_area_km2(DroughtSeverity.EXTREME)
            }
        }
    
    def to_geojson(self) -> Dict:
        """Exporte les zones en GeoJSON"""
        from core.module2.utils import get_bounding_box, create_risk_color_scale
        
        color_scale = create_risk_color_scale('drought')
        features = []
        
        for zone in self.zones:
            # Créer bbox autour du centre
            radius_km = np.sqrt(zone.area_km2 / np.pi)
            bbox = get_bounding_box(zone.center_lat, zone.center_lon, radius_km)
            
            geometry = {
                "type": "Polygon",
                "coordinates": [[
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                    [bbox[0], bbox[1]]
                ]]
            }
            
            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    **zone.to_dict(),
                    "color": color_scale.get(zone.severity.value, "#999999")
                }
            }
            
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_zones": len(features)
            }
        }
    
    def __len__(self) -> int:
        return len(self.zones)
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"DroughtZoneAnalyzer(zones={stats['total_zones']}, "
            f"critical={stats['critical_zones']})"
        )