# core/module2/zone_info.py
"""
Module 2 - Zone Information Provider
=====================================

Génération de fiches détaillées par zone géographique :
- Informations générales (commune, bassin versant, région)
- Indices et statistiques climatiques
- Historique des événements
- Alertes en cours et passées
- Impacts recensés
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum


class ZoneType(Enum):
    """Types de zones géographiques"""
    COMMUNE = "commune"
    BASSIN_VERSANT = "bassin_versant"
    REGION = "region"
    DEPARTEMENT = "departement"
    ARRONDISSEMENT = "arrondissement"
    CUSTOM = "custom"


@dataclass
class ClimateIndices:
    """
    Indices climatiques pour une zone
    
    Attributes:
        spi: Standardized Precipitation Index
        spei: Standardized Precipitation Evapotranspiration Index
        pdsi: Palmer Drought Severity Index
        temperature_anomaly: Anomalie de température (°C)
        precipitation_anomaly: Anomalie de précipitation (%)
        aridity_index: Indice d'aridité
    """
    spi: Optional[float] = None
    spei: Optional[float] = None
    pdsi: Optional[float] = None
    temperature_anomaly: Optional[float] = None
    precipitation_anomaly: Optional[float] = None
    aridity_index: Optional[float] = None
    
    def get_drought_severity(self) -> str:
        """
        Évalue la sévérité de la sécheresse basée sur SPI
        
        Returns:
            Sévérité ('none', 'mild', 'moderate', 'severe', 'extreme')
        """
        if self.spi is None:
            return 'unknown'
        
        if self.spi >= -0.5:
            return 'none'
        elif self.spi >= -1.0:
            return 'mild'
        elif self.spi >= -1.5:
            return 'moderate'
        elif self.spi >= -2.0:
            return 'severe'
        else:
            return 'extreme'
    
    def get_summary(self) -> Dict:
        """
        Résumé des indices
        
        Returns:
            Dictionnaire descriptif
        """
        return {
            'drought_severity': self.get_drought_severity(),
            'spi': round(self.spi, 2) if self.spi is not None else None,
            'spei': round(self.spei, 2) if self.spei is not None else None,
            'temp_anomaly': round(self.temperature_anomaly, 1) if self.temperature_anomaly is not None else None,
            'precip_anomaly': round(self.precipitation_anomaly, 1) if self.precipitation_anomaly is not None else None
        }


@dataclass
class HistoricalEvent:
    """
    Événement climatique historique
    
    Attributes:
        event_type: Type d'événement
        date: Date de l'événement
        severity: Sévérité
        description: Description
        impacts: Impacts recensés
        sources: Sources d'information
    """
    event_type: str
    date: date
    severity: str
    description: str
    impacts: Dict[str, any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    
    def get_impact_summary(self) -> str:
        """
        Résumé des impacts
        
        Returns:
            Texte descriptif
        """
        parts = []
        
        if 'population_affected' in self.impacts:
            parts.append(f"{self.impacts['population_affected']:,} personnes affectées")
        
        if 'economic_loss' in self.impacts:
            parts.append(f"{self.impacts['economic_loss']:,} FCFA de pertes")
        
        if 'infrastructure_damage' in self.impacts:
            parts.append(f"{self.impacts['infrastructure_damage']} infrastructures endommagées")
        
        return ", ".join(parts) if parts else "Impacts non documentés"


@dataclass
class ActiveAlert:
    """
    Alerte active pour une zone
    
    Attributes:
        alert_type: Type d'alerte
        level: Niveau (yellow, orange, red, extreme)
        issued_at: Date/heure d'émission
        expires_at: Date/heure d'expiration
        description: Description
        recommendations: Recommandations
    """
    alert_type: str
    level: str
    issued_at: datetime
    expires_at: datetime
    description: str
    recommendations: List[str] = field(default_factory=list)
    
    def is_active(self) -> bool:
        """Vérifie si l'alerte est toujours active"""
        return datetime.now() < self.expires_at
    
    def time_remaining(self) -> str:
        """
        Temps restant avant expiration
        
        Returns:
            Texte formaté
        """
        if not self.is_active():
            return "Expirée"
        
        delta = self.expires_at - datetime.now()
        
        if delta.days > 0:
            return f"{delta.days} jour{'s' if delta.days > 1 else ''}"
        
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours} heure{'s' if hours > 1 else ''}"
        
        minutes = (delta.seconds % 3600) // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''}"


@dataclass
class ZoneDetails:
    """
    Détails complets d'une zone géographique
    
    Attributes:
        zone_id: Identifiant unique
        zone_name: Nom de la zone
        zone_type: Type de zone
        geometry: Géométrie (GeoJSON)
        center_lat: Latitude centre
        center_lon: Longitude centre
        area_km2: Surface (km²)
        population: Population
        climate_indices: Indices climatiques
        historical_events: Événements historiques
        active_alerts: Alertes actives
        metadata: Métadonnées additionnelles
    """
    zone_id: str
    zone_name: str
    zone_type: ZoneType
    geometry: Dict
    center_lat: float
    center_lon: float
    area_km2: float
    population: Optional[int] = None
    climate_indices: Optional[ClimateIndices] = None
    historical_events: List[HistoricalEvent] = field(default_factory=list)
    active_alerts: List[ActiveAlert] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def get_risk_status(self) -> Dict:
        """
        Évalue le statut de risque global de la zone
        
        Returns:
            Statut multi-risques
        """
        risks = {
            'flood': 'low',
            'drought': 'low',
            'overall': 'low'
        }
        
        # Analyser alertes actives
        for alert in self.active_alerts:
            if not alert.is_active():
                continue
            
            if alert.alert_type == 'flood':
                if alert.level in ['red', 'extreme']:
                    risks['flood'] = 'critical'
                elif alert.level == 'orange' and risks['flood'] != 'critical':
                    risks['flood'] = 'high'
                elif alert.level == 'yellow' and risks['flood'] not in ['critical', 'high']:
                    risks['flood'] = 'moderate'
            
            elif alert.alert_type == 'drought':
                if alert.level in ['red', 'extreme']:
                    risks['drought'] = 'critical'
                elif alert.level == 'orange' and risks['drought'] != 'critical':
                    risks['drought'] = 'high'
                elif alert.level == 'yellow' and risks['drought'] not in ['critical', 'high']:
                    risks['drought'] = 'moderate'
        
        # Analyser indices climatiques
        if self.climate_indices:
            severity = self.climate_indices.get_drought_severity()
            
            if severity == 'extreme' and risks['drought'] != 'critical':
                risks['drought'] = 'critical'
            elif severity == 'severe' and risks['drought'] not in ['critical', 'high']:
                risks['drought'] = 'high'
            elif severity == 'moderate' and risks['drought'] not in ['critical', 'high', 'moderate']:
                risks['drought'] = 'moderate'
        
        # Risque global = max des risques
        all_risk_levels = [risks['flood'], risks['drought']]
        
        if 'critical' in all_risk_levels:
            risks['overall'] = 'critical'
        elif 'high' in all_risk_levels:
            risks['overall'] = 'high'
        elif 'moderate' in all_risk_levels:
            risks['overall'] = 'moderate'
        
        return risks
    
    def get_recent_events(self, days: int = 30) -> List[HistoricalEvent]:
        """
        Récupère les événements récents
        
        Args:
            days: Nombre de jours
        
        Returns:
            Événements récents
        """
        cutoff_date = date.today() - timedelta(days=days)
        
        return [
            event for event in self.historical_events
            if event.date >= cutoff_date
        ]
    
    def count_events_by_type(self) -> Dict[str, int]:
        """
        Compte les événements par type
        
        Returns:
            Dictionnaire {type: count}
        """
        counts = {}
        
        for event in self.historical_events:
            event_type = event.event_type
            counts[event_type] = counts.get(event_type, 0) + 1
        
        return counts
    
    def to_summary_dict(self) -> Dict:
        """
        Résumé compact pour affichage
        
        Returns:
            Dictionnaire descriptif
        """
        risk_status = self.get_risk_status()
        recent_events = self.get_recent_events()
        event_counts = self.count_events_by_type()
        
        return {
            'zone_id': self.zone_id,
            'zone_name': self.zone_name,
            'zone_type': self.zone_type.value,
            'center': {'lat': self.center_lat, 'lon': self.center_lon},
            'area_km2': round(self.area_km2, 2),
            'population': self.population,
            'risk_status': risk_status,
            'climate_indices': self.climate_indices.get_summary() if self.climate_indices else None,
            'active_alerts_count': len([a for a in self.active_alerts if a.is_active()]),
            'recent_events_count': len(recent_events),
            'historical_events_by_type': event_counts,
            'metadata': self.metadata
        }


class ZoneInfoProvider:
    """
    Fournisseur d'informations détaillées par zone
    
    Permet de :
    - Récupérer les détails d'une zone
    - Générer des fiches complètes
    - Comparer plusieurs zones
    - Exporter les informations
    """
    
    def __init__(self):
        self.zones: Dict[str, ZoneDetails] = {}
    
    def add_zone(self, zone: ZoneDetails) -> None:
        """
        Ajoute une zone au provider
        
        Args:
            zone: Détails de la zone
        """
        self.zones[zone.zone_id] = zone
    
    def get_zone(self, zone_id: str) -> Optional[ZoneDetails]:
        """
        Récupère une zone par ID
        
        Args:
            zone_id: Identifiant de la zone
        
        Returns:
            ZoneDetails ou None
        """
        return self.zones.get(zone_id)
    
    def find_zones_by_name(self, name: str) -> List[ZoneDetails]:
        """
        Recherche des zones par nom (recherche partielle)
        
        Args:
            name: Nom à rechercher
        
        Returns:
            Liste des zones correspondantes
        """
        name_lower = name.lower()
        
        return [
            zone for zone in self.zones.values()
            if name_lower in zone.zone_name.lower()
        ]
    
    def get_zones_in_bbox(
        self,
        bbox: Tuple[float, float, float, float]
    ) -> List[ZoneDetails]:
        """
        Récupère les zones dans une bounding box
        
        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat)
        
        Returns:
            Zones dans la bbox
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        
        return [
            zone for zone in self.zones.values()
            if (min_lon <= zone.center_lon <= max_lon and
                min_lat <= zone.center_lat <= max_lat)
        ]
    
    def get_critical_zones(self) -> List[ZoneDetails]:
        """
        Récupère les zones en situation critique
        
        Returns:
            Zones critiques
        """
        critical = []
        
        for zone in self.zones.values():
            risk_status = zone.get_risk_status()
            
            if risk_status['overall'] == 'critical':
                critical.append(zone)
        
        return critical
    
    def generate_zone_report(self, zone_id: str) -> Optional[Dict]:
        """
        Génère un rapport complet pour une zone
        
        Args:
            zone_id: Identifiant de la zone
        
        Returns:
            Rapport détaillé ou None
        """
        zone = self.get_zone(zone_id)
        
        if not zone:
            return None
        
        risk_status = zone.get_risk_status()
        recent_events = zone.get_recent_events(days=30)
        
        return {
            'zone_info': {
                'id': zone.zone_id,
                'name': zone.zone_name,
                'type': zone.zone_type.value,
                'area_km2': zone.area_km2,
                'population': zone.population,
                'coordinates': {
                    'lat': zone.center_lat,
                    'lon': zone.center_lon
                }
            },
            'risk_assessment': risk_status,
            'climate_indices': zone.climate_indices.get_summary() if zone.climate_indices else None,
            'active_alerts': [
                {
                    'type': alert.alert_type,
                    'level': alert.level,
                    'description': alert.description,
                    'time_remaining': alert.time_remaining(),
                    'recommendations': alert.recommendations
                }
                for alert in zone.active_alerts
                if alert.is_active()
            ],
            'recent_events': [
                {
                    'type': event.event_type,
                    'date': event.date.strftime('%d/%m/%Y'),
                    'severity': event.severity,
                    'description': event.description,
                    'impacts': event.get_impact_summary()
                }
                for event in recent_events
            ],
            'historical_summary': {
                'total_events': len(zone.historical_events),
                'events_by_type': zone.count_events_by_type(),
                'recent_events_30d': len(recent_events)
            },
            'metadata': zone.metadata
        }
    
    def compare_zones(
        self,
        zone_ids: List[str],
        criteria: List[str] = None
    ) -> Dict:
        """
        Compare plusieurs zones selon des critères
        
        Args:
            zone_ids: Liste des IDs de zones
            criteria: Critères de comparaison (optionnel)
        
        Returns:
            Tableau comparatif
        """
        if criteria is None:
            criteria = ['area_km2', 'population', 'risk_status', 'alert_count']
        
        comparison = {
            'zones': [],
            'criteria': criteria
        }
        
        for zone_id in zone_ids:
            zone = self.get_zone(zone_id)
            
            if not zone:
                continue
            
            zone_data = {
                'id': zone.zone_id,
                'name': zone.zone_name
            }
            
            if 'area_km2' in criteria:
                zone_data['area_km2'] = round(zone.area_km2, 2)
            
            if 'population' in criteria:
                zone_data['population'] = zone.population
            
            if 'risk_status' in criteria:
                zone_data['risk_status'] = zone.get_risk_status()
            
            if 'alert_count' in criteria:
                zone_data['alert_count'] = len([a for a in zone.active_alerts if a.is_active()])
            
            if 'event_count' in criteria:
                zone_data['event_count'] = len(zone.historical_events)
            
            comparison['zones'].append(zone_data)
        
        return comparison
    
    def export_zones(
        self,
        zone_ids: Optional[List[str]] = None,
        format: str = 'summary'
    ) -> List[Dict]:
        """
        Exporte les données des zones
        
        Args:
            zone_ids: IDs des zones (None = toutes)
            format: 'summary' ou 'full'
        
        Returns:
            Liste de dictionnaires
        """
        zones_to_export = []
        
        if zone_ids:
            zones_to_export = [
                self.zones[zid] for zid in zone_ids
                if zid in self.zones
            ]
        else:
            zones_to_export = list(self.zones.values())
        
        if format == 'summary':
            return [zone.to_summary_dict() for zone in zones_to_export]
        
        elif format == 'full':
            return [
                self.generate_zone_report(zone.zone_id)
                for zone in zones_to_export
            ]
        
        else:
            raise ValueError(f"Format non supporté : {format}")
    
    def __len__(self) -> int:
        """Nombre de zones"""
        return len(self.zones)
    
    def __repr__(self) -> str:
        return f"ZoneInfoProvider(zones={len(self.zones)})"