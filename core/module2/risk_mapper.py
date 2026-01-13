# core/module2/risk_mapper.py
"""
Module 2 - Risk Mapper
Cartographie interactive des zones à risque climatique
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from datetime import datetime, date

from core.module2.utils import (
    create_risk_color_scale,
    get_risk_level_label,
    format_area,
    get_bounding_box
)


class RiskType(Enum):
    """Types de risques climatiques"""
    FLOOD = "flood"
    DROUGHT = "drought"
    HEAT = "heat"
    EROSION = "erosion"
    STORM = "storm"
    MULTI = "multi"


@dataclass
class RiskLayer:
    """
    Couche de risque cartographique
    
    Attributes:
        risk_type: Type de risque
        level: Niveau de risque (low, moderate, high, critical, extreme)
        geometry: Géométrie de la zone (polygone)
        properties: Propriétés additionnelles
        timestamp: Date/heure de l'analyse
    """
    risk_type: RiskType
    level: str
    geometry: Dict  # GeoJSON polygon
    properties: Dict
    timestamp: datetime
    
    def to_geojson_feature(self) -> Dict:
        """Convertit en feature GeoJSON"""
        color_scale = create_risk_color_scale(self.risk_type.value)
        
        return {
            "type": "Feature",
            "geometry": self.geometry,
            "properties": {
                **self.properties,
                "risk_type": self.risk_type.value,
                "risk_level": self.level,
                "risk_label": get_risk_level_label(self.level, self.risk_type.value),
                "color": color_scale.get(self.level, "#999999"),
                "timestamp": self.timestamp.isoformat()
            }
        }


class RiskMapper:
    """
    Gestionnaire de cartographie des risques climatiques
    
    Fonctionnalités:
    - Création de couches de risque multi-types
    - Agrégation spatiale
    - Export GeoJSON pour visualisation
    - Filtrage temporel et spatial
    """
    
    def __init__(self):
        self.layers: List[RiskLayer] = []
        self.current_bbox: Optional[Tuple[float, float, float, float]] = None
    
    def add_layer(self, layer: RiskLayer) -> None:
        """
        Ajoute une couche de risque
        
        Args:
            layer: Couche à ajouter
        """
        self.layers.append(layer)
    
    def create_flood_layer(
        self,
        zone_name: str,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        risk_level: str,
        properties: Optional[Dict] = None
    ) -> RiskLayer:
        """
        Crée une couche de risque d'inondation
        
        Args:
            zone_name: Nom de la zone
            center_lat: Latitude centre
            center_lon: Longitude centre
            radius_km: Rayon de la zone
            risk_level: Niveau de risque
            properties: Propriétés additionnelles
        
        Returns:
            RiskLayer créée
        """
        # Créer un polygone circulaire approximatif
        bbox = get_bounding_box(center_lat, center_lon, radius_km)
        
        # Créer polygone GeoJSON (rectangle pour simplifier)
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [bbox[0], bbox[1]],  # SW
                [bbox[2], bbox[1]],  # SE
                [bbox[2], bbox[3]],  # NE
                [bbox[0], bbox[3]],  # NW
                [bbox[0], bbox[1]]   # Close
            ]]
        }
        
        # Propriétés
        layer_properties = {
            "zone_name": zone_name,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "radius_km": radius_km,
            "area_km2": (radius_km ** 2) * np.pi,
            **(properties or {})
        }
        
        layer = RiskLayer(
            risk_type=RiskType.FLOOD,
            level=risk_level,
            geometry=geometry,
            properties=layer_properties,
            timestamp=datetime.now()
        )
        
        self.add_layer(layer)
        return layer
    
    def create_drought_layer(
        self,
        zone_name: str,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        severity: str,
        properties: Optional[Dict] = None
    ) -> RiskLayer:
        """
        Crée une couche de risque de sécheresse
        
        Args:
            zone_name: Nom de la zone
            center_lat: Latitude centre
            center_lon: Longitude centre
            radius_km: Rayon de la zone
            severity: Sévérité de la sécheresse
            properties: Propriétés additionnelles
        
        Returns:
            RiskLayer créée
        """
        bbox = get_bounding_box(center_lat, center_lon, radius_km)
        
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
        
        layer_properties = {
            "zone_name": zone_name,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "radius_km": radius_km,
            "area_km2": (radius_km ** 2) * np.pi,
            **(properties or {})
        }
        
        layer = RiskLayer(
            risk_type=RiskType.DROUGHT,
            level=severity,
            geometry=geometry,
            properties=layer_properties,
            timestamp=datetime.now()
        )
        
        self.add_layer(layer)
        return layer
    
    def get_layers_by_type(self, risk_type: RiskType) -> List[RiskLayer]:
        """
        Récupère les couches d'un type spécifique
        
        Args:
            risk_type: Type de risque
        
        Returns:
            Liste des couches correspondantes
        """
        return [layer for layer in self.layers if layer.risk_type == risk_type]
    
    def get_layers_by_level(self, level: str) -> List[RiskLayer]:
        """
        Récupère les couches d'un niveau spécifique
        
        Args:
            level: Niveau de risque
        
        Returns:
            Liste des couches correspondantes
        """
        return [layer for layer in self.layers if layer.level == level]
    
    def filter_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[RiskLayer]:
        """
        Filtre les couches par période
        
        Args:
            start_date: Date de début
            end_date: Date de fin
        
        Returns:
            Couches filtrées
        """
        return [
            layer for layer in self.layers
            if start_date <= layer.timestamp <= end_date
        ]
    
    def filter_by_bbox(
        self,
        bbox: Tuple[float, float, float, float]
    ) -> List[RiskLayer]:
        """
        Filtre les couches par zone géographique
        
        Args:
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
        
        Returns:
            Couches dans la bbox
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        
        filtered = []
        for layer in self.layers:
            # Vérifier si le centre de la zone est dans la bbox
            center_lat = layer.properties.get('center_lat')
            center_lon = layer.properties.get('center_lon')
            
            if center_lat and center_lon:
                if (min_lon <= center_lon <= max_lon and 
                    min_lat <= center_lat <= max_lat):
                    filtered.append(layer)
        
        return filtered
    
    def to_geojson(
        self,
        risk_type: Optional[RiskType] = None,
        level: Optional[str] = None
    ) -> Dict:
        """
        Exporte les couches en GeoJSON
        
        Args:
            risk_type: Filtrer par type (optionnel)
            level: Filtrer par niveau (optionnel)
        
        Returns:
            FeatureCollection GeoJSON
        """
        layers = self.layers
        
        # Appliquer filtres
        if risk_type:
            layers = [l for l in layers if l.risk_type == risk_type]
        
        if level:
            layers = [l for l in layers if l.level == level]
        
        features = [layer.to_geojson_feature() for layer in layers]
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_layers": len(features),
                "risk_type": risk_type.value if risk_type else "all",
                "level": level if level else "all"
            }
        }
    
    def get_statistics(self) -> Dict:
        """
        Calcule des statistiques sur les couches
        
        Returns:
            Statistiques globales
        """
        if not self.layers:
            return {
                "total_layers": 0,
                "by_type": {},
                "by_level": {},
                "total_area_km2": 0
            }
        
        # Par type
        by_type = {}
        for risk_type in RiskType:
            count = len(self.get_layers_by_type(risk_type))
            if count > 0:
                by_type[risk_type.value] = count
        
        # Par niveau
        all_levels = set(layer.level for layer in self.layers)
        by_level = {
            level: len(self.get_layers_by_level(level))
            for level in all_levels
        }
        
        # Surface totale
        total_area = sum(
            layer.properties.get('area_km2', 0)
            for layer in self.layers
        )
        
        return {
            "total_layers": len(self.layers),
            "by_type": by_type,
            "by_level": by_level,
            "total_area_km2": total_area,
            "formatted_area": format_area(total_area)
        }
    
    def get_critical_zones(self) -> List[RiskLayer]:
        """
        Récupère les zones critiques (critical + extreme)
        
        Returns:
            Liste des zones critiques
        """
        return [
            layer for layer in self.layers
            if layer.level in ['critical', 'extreme', 'exceptional']
        ]
    
    def clear(self) -> None:
        """Efface toutes les couches"""
        self.layers = []
    
    def __len__(self) -> int:
        """Nombre de couches"""
        return len(self.layers)
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"RiskMapper(layers={stats['total_layers']}, "
            f"area={stats['formatted_area']})"
        )