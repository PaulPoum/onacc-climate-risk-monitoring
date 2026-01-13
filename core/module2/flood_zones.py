# core/module2/flood_zones.py
"""
Module 2 - Flood Zones Analyzer
Analyse et cartographie des zones inondables
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import numpy as np

from core.module2.utils import (
    classify_flood_risk,
    get_risk_level_label,
    format_area
)


class FloodRiskLevel(Enum):
    """Niveaux de risque d'inondation"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    EXTREME = "extreme"


class FloodZoneType(Enum):
    """Types de zones inondables"""
    FLOODPLAIN = "floodplain"  # Plaine alluviale
    URBAN = "urban"            # Zone urbaine sensible
    MAJOR_BED = "major_bed"    # Lit majeur
    COASTAL = "coastal"        # Zone côtière
    FLASH_FLOOD = "flash_flood" # Zone de crue rapide


@dataclass
class FloodZone:
    """
    Zone inondable
    
    Attributes:
        zone_id: Identifiant unique
        name: Nom de la zone
        zone_type: Type de zone
        risk_level: Niveau de risque actuel
        center_lat: Latitude centre
        center_lon: Longitude centre
        area_km2: Surface en km²
        population: Population exposée
        return_period_years: Période de retour (années)
        properties: Propriétés additionnelles
    """
    zone_id: str
    name: str
    zone_type: FloodZoneType
    risk_level: FloodRiskLevel
    center_lat: float
    center_lon: float
    area_km2: float
    population: Optional[int] = None
    return_period_years: Optional[int] = None
    properties: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "zone_type": self.zone_type.value,
            "risk_level": self.risk_level.value,
            "risk_label": get_risk_level_label(self.risk_level.value, 'flood'),
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "area_km2": self.area_km2,
            "formatted_area": format_area(self.area_km2),
            "population": self.population,
            "return_period_years": self.return_period_years,
            "properties": self.properties or {}
        }


class FloodZoneAnalyzer:
    """
    Analyseur de zones inondables
    
    Fonctionnalités:
    - Identification des zones à risque
    - Calcul du risque basé sur hydrologie
    - Estimation population exposée
    - Cartographie des zones inondables
    """
    
    # Zones pré-définies pour le Cameroun
    CAMEROON_FLOOD_ZONES = {
        "logone": {
            "name": "Plaine du Logone",
            "zone_type": FloodZoneType.FLOODPLAIN,
            "center_lat": 10.5,
            "center_lon": 15.0,
            "area_km2": 8000,
            "population": 500000,
            "watershed": "Logone"
        },
        "wouri": {
            "name": "Estuaire du Wouri",
            "zone_type": FloodZoneType.COASTAL,
            "center_lat": 4.05,
            "center_lon": 9.7,
            "area_km2": 1200,
            "population": 250000,
            "watershed": "Wouri"
        },
        "sanaga": {
            "name": "Bassin de la Sanaga",
            "zone_type": FloodZoneType.MAJOR_BED,
            "center_lat": 4.5,
            "center_lon": 11.5,
            "area_km2": 3500,
            "population": 180000,
            "watershed": "Sanaga"
        },
        "douala_urban": {
            "name": "Douala Centre",
            "zone_type": FloodZoneType.URBAN,
            "center_lat": 4.05,
            "center_lon": 9.7,
            "area_km2": 150,
            "population": 400000,
            "watershed": "Wouri"
        },
        "yaounde_urban": {
            "name": "Yaoundé Centre",
            "zone_type": FloodZoneType.URBAN,
            "center_lat": 3.848,
            "center_lon": 11.502,
            "area_km2": 80,
            "population": 300000,
            "watershed": "Mfoundi"
        }
    }
    
    def __init__(self):
        self.zones: List[FloodZone] = []
        self._load_predefined_zones()
    
    def _load_predefined_zones(self):
        """Charge les zones pré-définies"""
        for zone_id, data in self.CAMEROON_FLOOD_ZONES.items():
            zone = FloodZone(
                zone_id=zone_id,
                name=data["name"],
                zone_type=data["zone_type"],
                risk_level=FloodRiskLevel.LOW,  # Par défaut
                center_lat=data["center_lat"],
                center_lon=data["center_lon"],
                area_km2=data["area_km2"],
                population=data.get("population"),
                properties={"watershed": data.get("watershed")}
            )
            self.zones.append(zone)
    
    def analyze_zone(
        self,
        zone_id: str,
        precipitation_mm: float,
        discharge_m3s: Optional[float] = None,
        water_level_m: Optional[float] = None
    ) -> FloodZone:
        """
        Analyse le risque d'inondation pour une zone
        
        Args:
            zone_id: ID de la zone
            precipitation_mm: Précipitations prévues/observées
            discharge_m3s: Débit (optionnel)
            water_level_m: Niveau d'eau (optionnel)
        
        Returns:
            Zone avec risque actualisé
        """
        # Trouver la zone
        zone = self.get_zone(zone_id)
        if not zone:
            raise ValueError(f"Zone {zone_id} non trouvée")
        
        # Classifier le risque
        risk_level_str = classify_flood_risk(
            precipitation_mm,
            discharge_m3s,
            water_level_m
        )
        
        # Mettre à jour
        zone.risk_level = FloodRiskLevel(risk_level_str)
        
        # Calculer période de retour approximative
        if risk_level_str == 'extreme':
            zone.return_period_years = 100
        elif risk_level_str == 'critical':
            zone.return_period_years = 50
        elif risk_level_str == 'high':
            zone.return_period_years = 20
        elif risk_level_str == 'moderate':
            zone.return_period_years = 10
        else:
            zone.return_period_years = 5
        
        return zone
    
    def get_zone(self, zone_id: str) -> Optional[FloodZone]:
        """
        Récupère une zone par ID
        
        Args:
            zone_id: ID de la zone
        
        Returns:
            FloodZone ou None
        """
        for zone in self.zones:
            if zone.zone_id == zone_id:
                return zone
        return None
    
    def get_zones_by_risk(self, risk_level: FloodRiskLevel) -> List[FloodZone]:
        """
        Récupère les zones d'un niveau de risque donné
        
        Args:
            risk_level: Niveau de risque
        
        Returns:
            Liste des zones
        """
        return [z for z in self.zones if z.risk_level == risk_level]
    
    def get_critical_zones(self) -> List[FloodZone]:
        """
        Récupère les zones critiques
        
        Returns:
            Zones avec risque critical ou extreme
        """
        return [
            z for z in self.zones
            if z.risk_level in [FloodRiskLevel.CRITICAL, FloodRiskLevel.EXTREME]
        ]
    
    def get_exposed_population(self, risk_threshold: FloodRiskLevel = FloodRiskLevel.MODERATE) -> int:
        """
        Calcule la population exposée
        
        Args:
            risk_threshold: Seuil de risque minimum
        
        Returns:
            Population totale exposée
        """
        risk_values = {
            FloodRiskLevel.LOW: 0,
            FloodRiskLevel.MODERATE: 1,
            FloodRiskLevel.HIGH: 2,
            FloodRiskLevel.CRITICAL: 3,
            FloodRiskLevel.EXTREME: 4
        }
        
        threshold_value = risk_values[risk_threshold]
        
        total = 0
        for zone in self.zones:
            if risk_values[zone.risk_level] >= threshold_value:
                if zone.population:
                    total += zone.population
        
        return total
    
    def get_affected_area_km2(self, risk_threshold: FloodRiskLevel = FloodRiskLevel.MODERATE) -> float:
        """
        Calcule la surface totale affectée
        
        Args:
            risk_threshold: Seuil de risque minimum
        
        Returns:
            Surface en km²
        """
        risk_values = {
            FloodRiskLevel.LOW: 0,
            FloodRiskLevel.MODERATE: 1,
            FloodRiskLevel.HIGH: 2,
            FloodRiskLevel.CRITICAL: 3,
            FloodRiskLevel.EXTREME: 4
        }
        
        threshold_value = risk_values[risk_threshold]
        
        total = 0
        for zone in self.zones:
            if risk_values[zone.risk_level] >= threshold_value:
                total += zone.area_km2
        
        return total
    
    def get_statistics(self) -> Dict:
        """
        Calcule des statistiques globales
        
        Returns:
            Dictionnaire de statistiques
        """
        by_risk = {}
        for level in FloodRiskLevel:
            zones = self.get_zones_by_risk(level)
            if zones:
                by_risk[level.value] = {
                    "count": len(zones),
                    "zones": [z.name for z in zones]
                }
        
        critical_zones = self.get_critical_zones()
        
        return {
            "total_zones": len(self.zones),
            "critical_zones": len(critical_zones),
            "by_risk_level": by_risk,
            "exposed_population": {
                "moderate_plus": self.get_exposed_population(FloodRiskLevel.MODERATE),
                "high_plus": self.get_exposed_population(FloodRiskLevel.HIGH),
                "critical_plus": self.get_exposed_population(FloodRiskLevel.CRITICAL)
            },
            "affected_area_km2": {
                "moderate_plus": self.get_affected_area_km2(FloodRiskLevel.MODERATE),
                "high_plus": self.get_affected_area_km2(FloodRiskLevel.HIGH),
                "critical_plus": self.get_affected_area_km2(FloodRiskLevel.CRITICAL)
            }
        }
    
    def to_geojson(self) -> Dict:
        """
        Exporte les zones en GeoJSON
        
        Returns:
            FeatureCollection GeoJSON
        """
        from core.module2.utils import get_bounding_box, create_risk_color_scale
        
        color_scale = create_risk_color_scale('flood')
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
                    "color": color_scale.get(zone.risk_level.value, "#999999")
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
            f"FloodZoneAnalyzer(zones={stats['total_zones']}, "
            f"critical={stats['critical_zones']})"
        )