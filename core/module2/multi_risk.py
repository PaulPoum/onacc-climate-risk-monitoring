# core/module2/multi_risk.py
"""
Module 2 - Multi-Risk Analyzer
Analyse et agrégation de risques climatiques multiples
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import numpy as np

from core.module2.flood_zones import FloodZoneAnalyzer, FloodRiskLevel
from core.module2.drought_zones import DroughtZoneAnalyzer, DroughtSeverity
from core.module2.utils import get_risk_level_label, format_area


class RiskType(Enum):
    """Types de risques climatiques"""
    FLOOD = "flood"
    DROUGHT = "drought"
    HEAT = "heat"
    STORM = "storm"
    EROSION = "erosion"
    LANDSLIDE = "landslide"


@dataclass
class CompositeRisk:
    """
    Risque composite pour une zone
    
    Attributes:
        zone_id: Identifiant de la zone
        zone_name: Nom de la zone
        risks: Dictionnaire {type_risque: niveau}
        composite_score: Score composite (0-100)
        priority_level: Niveau de priorité
        center_lat: Latitude
        center_lon: Longitude
        area_km2: Surface
        population: Population
    """
    zone_id: str
    zone_name: str
    risks: Dict[RiskType, str]
    composite_score: float
    priority_level: str
    center_lat: float
    center_lon: float
    area_km2: float
    population: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "risks": {k.value: v for k, v in self.risks.items()},
            "composite_score": self.composite_score,
            "priority_level": self.priority_level,
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "area_km2": self.area_km2,
            "formatted_area": format_area(self.area_km2),
            "population": self.population
        }


class MultiRiskAnalyzer:
    """
    Analyseur multi-risques
    
    Combine plusieurs types de risques pour identifier les zones
    les plus vulnérables nécessitant une attention prioritaire.
    
    Fonctionnalités:
    - Agrégation de risques multiples
    - Calcul de score composite
    - Priorisation des zones
    - Cartographie intégrée
    """
    
    def __init__(self):
        self.flood_analyzer = FloodZoneAnalyzer()
        self.drought_analyzer = DroughtZoneAnalyzer()
        self.composite_risks: List[CompositeRisk] = []
    
    def calculate_composite_score(
        self,
        risks: Dict[RiskType, str],
        weights: Optional[Dict[RiskType, float]] = None
    ) -> float:
        """
        Calcule un score composite de risque
        
        Args:
            risks: Dictionnaire {type_risque: niveau}
            weights: Poids par type (optionnel, par défaut égaux)
        
        Returns:
            Score composite (0-100)
        """
        # Valeurs numériques par niveau
        flood_values = {
            'low': 10,
            'moderate': 30,
            'high': 50,
            'critical': 75,
            'extreme': 100
        }
        
        drought_values = {
            'normal': 0,
            'abnormally_dry': 15,
            'moderate': 30,
            'severe': 55,
            'extreme': 80,
            'exceptional': 100
        }
        
        heat_values = {
            'normal': 0,
            'caution': 20,
            'extreme_caution': 40,
            'danger': 70,
            'extreme_danger': 100
        }
        
        # Mapping type -> valeurs
        value_maps = {
            RiskType.FLOOD: flood_values,
            RiskType.DROUGHT: drought_values,
            RiskType.HEAT: heat_values
        }
        
        # Poids par défaut
        if weights is None:
            weights = {risk_type: 1.0 for risk_type in risks.keys()}
        
        # Calculer score pondéré
        total_score = 0
        total_weight = 0
        
        for risk_type, level in risks.items():
            value_map = value_maps.get(risk_type, flood_values)
            value = value_map.get(level, 0)
            weight = weights.get(risk_type, 1.0)
            
            total_score += value * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0
        
        # Score normalisé 0-100
        return total_score / total_weight
    
    def classify_priority(self, composite_score: float) -> str:
        """
        Classifie le niveau de priorité
        
        Args:
            composite_score: Score composite
        
        Returns:
            Niveau de priorité
        """
        if composite_score >= 80:
            return 'critical'
        elif composite_score >= 60:
            return 'high'
        elif composite_score >= 40:
            return 'moderate'
        elif composite_score >= 20:
            return 'low'
        else:
            return 'minimal'
    
    def analyze_zone_multi_risk(
        self,
        zone_id: str,
        zone_name: str,
        center_lat: float,
        center_lon: float,
        area_km2: float,
        flood_risk: Optional[str] = None,
        drought_risk: Optional[str] = None,
        heat_risk: Optional[str] = None,
        population: Optional[int] = None,
        weights: Optional[Dict[RiskType, float]] = None
    ) -> CompositeRisk:
        """
        Analyse multi-risques pour une zone
        
        Args:
            zone_id: ID de la zone
            zone_name: Nom de la zone
            center_lat: Latitude
            center_lon: Longitude
            area_km2: Surface
            flood_risk: Risque inondation (optionnel)
            drought_risk: Risque sécheresse (optionnel)
            heat_risk: Risque chaleur (optionnel)
            population: Population (optionnel)
            weights: Poids par type de risque (optionnel)
        
        Returns:
            CompositeRisk
        """
        # Construire dictionnaire des risques
        risks = {}
        
        if flood_risk:
            risks[RiskType.FLOOD] = flood_risk
        
        if drought_risk:
            risks[RiskType.DROUGHT] = drought_risk
        
        if heat_risk:
            risks[RiskType.HEAT] = heat_risk
        
        # Calculer score composite
        composite_score = self.calculate_composite_score(risks, weights)
        
        # Classifier priorité
        priority_level = self.classify_priority(composite_score)
        
        # Créer CompositeRisk
        composite = CompositeRisk(
            zone_id=zone_id,
            zone_name=zone_name,
            risks=risks,
            composite_score=composite_score,
            priority_level=priority_level,
            center_lat=center_lat,
            center_lon=center_lon,
            area_km2=area_km2,
            population=population
        )
        
        self.composite_risks.append(composite)
        return composite
    
    def analyze_all_zones(self) -> List[CompositeRisk]:
        """
        Analyse toutes les zones connues
        
        Combine les analyses flood et drought pour créer
        une vue multi-risques complète.
        
        Returns:
            Liste de CompositeRisk
        """
        # Récupérer zones flood
        flood_zones = self.flood_analyzer.zones
        
        # Récupérer zones drought
        drought_zones = self.drought_analyzer.zones
        
        # Créer mapping zone_id -> risques
        zone_risks = {}
        
        # Ajouter risques flood
        for fz in flood_zones:
            if fz.zone_id not in zone_risks:
                zone_risks[fz.zone_id] = {
                    'name': fz.name,
                    'lat': fz.center_lat,
                    'lon': fz.center_lon,
                    'area': fz.area_km2,
                    'population': fz.population,
                    'risks': {}
                }
            zone_risks[fz.zone_id]['risks'][RiskType.FLOOD] = fz.risk_level.value
        
        # Ajouter risques drought
        for dz in drought_zones:
            if dz.zone_id not in zone_risks:
                zone_risks[dz.zone_id] = {
                    'name': dz.name,
                    'lat': dz.center_lat,
                    'lon': dz.center_lon,
                    'area': dz.area_km2,
                    'population': dz.population,
                    'risks': {}
                }
            zone_risks[dz.zone_id]['risks'][RiskType.DROUGHT] = dz.severity.value
        
        # Créer CompositeRisks
        self.composite_risks = []
        
        for zone_id, data in zone_risks.items():
            composite = self.analyze_zone_multi_risk(
                zone_id=zone_id,
                zone_name=data['name'],
                center_lat=data['lat'],
                center_lon=data['lon'],
                area_km2=data['area'],
                flood_risk=data['risks'].get(RiskType.FLOOD),
                drought_risk=data['risks'].get(RiskType.DROUGHT),
                population=data['population']
            )
        
        return self.composite_risks
    
    def get_priority_zones(self, priority_level: str) -> List[CompositeRisk]:
        """
        Récupère les zones d'un niveau de priorité donné
        
        Args:
            priority_level: Niveau de priorité
        
        Returns:
            Liste des zones
        """
        return [
            cr for cr in self.composite_risks
            if cr.priority_level == priority_level
        ]
    
    def get_top_priority_zones(self, n: int = 10) -> List[CompositeRisk]:
        """
        Récupère les N zones prioritaires
        
        Args:
            n: Nombre de zones à retourner
        
        Returns:
            Liste triée par score décroissant
        """
        sorted_risks = sorted(
            self.composite_risks,
            key=lambda x: x.composite_score,
            reverse=True
        )
        
        return sorted_risks[:n]
    
    def get_statistics(self) -> Dict:
        """Calcule des statistiques globales"""
        if not self.composite_risks:
            return {
                "total_zones": 0,
                "by_priority": {},
                "average_score": 0,
                "top_zones": []
            }
        
        by_priority = {}
        for priority in ['critical', 'high', 'moderate', 'low', 'minimal']:
            zones = self.get_priority_zones(priority)
            if zones:
                by_priority[priority] = {
                    "count": len(zones),
                    "zones": [z.zone_name for z in zones]
                }
        
        avg_score = np.mean([cr.composite_score for cr in self.composite_risks])
        
        top_zones = self.get_top_priority_zones(5)
        
        return {
            "total_zones": len(self.composite_risks),
            "by_priority": by_priority,
            "average_score": float(avg_score),
            "top_zones": [
                {
                    "name": z.zone_name,
                    "score": z.composite_score,
                    "priority": z.priority_level
                }
                for z in top_zones
            ]
        }
    
    def to_geojson(self) -> Dict:
        """Exporte en GeoJSON"""
        from core.module2.utils import get_bounding_box, create_risk_color_scale
        
        # Utiliser échelle de couleurs inondation pour priorité
        color_scale = {
            'critical': '#8b0000',
            'high': '#f44336',
            'moderate': '#ff9800',
            'low': '#ffc107',
            'minimal': '#4caf50'
        }
        
        features = []
        
        for cr in self.composite_risks:
            # Créer bbox
            radius_km = np.sqrt(cr.area_km2 / np.pi)
            bbox = get_bounding_box(cr.center_lat, cr.center_lon, radius_km)
            
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
                    **cr.to_dict(),
                    "color": color_scale.get(cr.priority_level, "#999999")
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
        return len(self.composite_risks)
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"MultiRiskAnalyzer(zones={stats['total_zones']}, "
            f"avg_score={stats['average_score']:.1f})"
        )