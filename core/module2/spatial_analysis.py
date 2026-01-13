# core/module2/spatial_analysis.py
"""
Module 2 - Spatial Analysis
Outils d'analyse spatiale et fiches d'information territoriale
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

from core.module2.utils import format_area, format_coordinates, format_population


@dataclass
class ZoneInfo:
    """
    Fiche d'information détaillée pour une zone
    
    Attributes:
        zone_id: Identifiant
        zone_name: Nom
        zone_type: Type (commune, bassin versant, région)
        center_lat: Latitude
        center_lon: Longitude
        area_km2: Surface
        population: Population
        climate_zone: Zone climatique
        watershed: Bassin versant
        elevation_m: Altitude moyenne
        land_use: Utilisation du sol
        risk_history: Historique des risques
        active_alerts: Alertes actives
        past_events: Événements passés
        impacts: Impacts recensés
        properties: Propriétés additionnelles
    """
    zone_id: str
    zone_name: str
    zone_type: str
    center_lat: float
    center_lon: float
    area_km2: float
    population: Optional[int] = None
    climate_zone: Optional[str] = None
    watershed: Optional[str] = None
    elevation_m: Optional[float] = None
    land_use: Optional[Dict[str, float]] = None
    risk_history: Optional[List[Dict]] = None
    active_alerts: Optional[List[Dict]] = None
    past_events: Optional[List[Dict]] = None
    impacts: Optional[Dict] = None
    properties: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "zone_type": self.zone_type,
            "center_coordinates": format_coordinates(self.center_lat, self.center_lon),
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "area_km2": self.area_km2,
            "formatted_area": format_area(self.area_km2),
            "population": self.population,
            "formatted_population": format_population(self.population) if self.population else "N/A",
            "climate_zone": self.climate_zone,
            "watershed": self.watershed,
            "elevation_m": self.elevation_m,
            "land_use": self.land_use,
            "risk_history": self.risk_history or [],
            "active_alerts": self.active_alerts or [],
            "past_events": self.past_events or [],
            "impacts": self.impacts or {},
            "properties": self.properties or {}
        }


class SpatialAnalyzer:
    """
    Analyseur spatial
    
    Fournit des outils d'analyse spatiale et génère des fiches
    d'information détaillées par zone d'intérêt.
    
    Fonctionnalités:
    - Fiches d'information par commune
    - Fiches par bassin versant
    - Historique des événements
    - Analyse temporelle des risques
    - Statistiques d'impact
    """
    
    # Données territoriales de base pour le Cameroun
    TERRITORIAL_DATA = {
        "communes": {
            "douala": {
                "name": "Douala",
                "type": "commune",
                "region": "Littoral",
                "department": "Wouri",
                "lat": 4.05,
                "lon": 9.7,
                "area_km2": 210,
                "population": 2800000,
                "climate_zone": "Équatorial côtier",
                "watershed": "Wouri",
                "elevation_m": 13
            },
            "yaounde": {
                "name": "Yaoundé",
                "type": "commune",
                "region": "Centre",
                "department": "Mfoundi",
                "lat": 3.848,
                "lon": 11.502,
                "area_km2": 304,
                "population": 3500000,
                "climate_zone": "Équatorial",
                "watershed": "Mfoundi",
                "elevation_m": 760
            },
            "garoua": {
                "name": "Garoua",
                "type": "commune",
                "region": "Nord",
                "department": "Bénoué",
                "lat": 9.3,
                "lon": 13.4,
                "area_km2": 85,
                "population": 600000,
                "climate_zone": "Soudano-sahélien",
                "watershed": "Bénoué",
                "elevation_m": 242
            },
            "maroua": {
                "name": "Maroua",
                "type": "commune",
                "region": "Extrême-Nord",
                "department": "Diamaré",
                "lat": 10.6,
                "lon": 14.3,
                "area_km2": 52,
                "population": 400000,
                "climate_zone": "Sahélien",
                "watershed": "Logone",
                "elevation_m": 423
            }
        },
        "watersheds": {
            "logone": {
                "name": "Bassin du Logone",
                "type": "bassin_versant",
                "lat": 10.5,
                "lon": 15.0,
                "area_km2": 75000,
                "population": 1500000,
                "climate_zone": "Soudano-sahélien",
                "main_river": "Logone"
            },
            "wouri": {
                "name": "Bassin du Wouri",
                "type": "bassin_versant",
                "lat": 4.5,
                "lon": 10.0,
                "area_km2": 12000,
                "population": 3000000,
                "climate_zone": "Équatorial",
                "main_river": "Wouri"
            },
            "sanaga": {
                "name": "Bassin de la Sanaga",
                "type": "bassin_versant",
                "lat": 4.5,
                "lon": 11.5,
                "area_km2": 140000,
                "population": 5000000,
                "climate_zone": "Équatorial",
                "main_river": "Sanaga"
            }
        }
    }
    
    def __init__(self):
        self.zones: Dict[str, ZoneInfo] = {}
        self._load_territorial_data()
    
    def _load_territorial_data(self):
        """Charge les données territoriales de base"""
        # Charger communes
        for zone_id, data in self.TERRITORIAL_DATA["communes"].items():
            zone_info = ZoneInfo(
                zone_id=zone_id,
                zone_name=data["name"],
                zone_type=data["type"],
                center_lat=data["lat"],
                center_lon=data["lon"],
                area_km2=data["area_km2"],
                population=data.get("population"),
                climate_zone=data.get("climate_zone"),
                watershed=data.get("watershed"),
                elevation_m=data.get("elevation_m"),
                properties={
                    "region": data.get("region"),
                    "department": data.get("department")
                }
            )
            self.zones[zone_id] = zone_info
        
        # Charger bassins versants
        for zone_id, data in self.TERRITORIAL_DATA["watersheds"].items():
            zone_info = ZoneInfo(
                zone_id=zone_id,
                zone_name=data["name"],
                zone_type=data["type"],
                center_lat=data["lat"],
                center_lon=data["lon"],
                area_km2=data["area_km2"],
                population=data.get("population"),
                climate_zone=data.get("climate_zone"),
                watershed=data.get("name"),
                properties={
                    "main_river": data.get("main_river")
                }
            )
            self.zones[zone_id] = zone_info
    
    def get_zone_info(self, zone_id: str) -> Optional[ZoneInfo]:
        """
        Récupère la fiche d'information d'une zone
        
        Args:
            zone_id: Identifiant de la zone
        
        Returns:
            ZoneInfo ou None
        """
        return self.zones.get(zone_id)
    
    def add_risk_history(
        self,
        zone_id: str,
        risk_type: str,
        risk_level: str,
        date: datetime,
        description: Optional[str] = None
    ):
        """
        Ajoute un événement à l'historique des risques
        
        Args:
            zone_id: ID de la zone
            risk_type: Type de risque
            risk_level: Niveau de risque
            date: Date de l'événement
            description: Description (optionnel)
        """
        zone = self.zones.get(zone_id)
        if not zone:
            return
        
        if zone.risk_history is None:
            zone.risk_history = []
        
        zone.risk_history.append({
            "risk_type": risk_type,
            "risk_level": risk_level,
            "date": date.isoformat(),
            "description": description
        })
    
    def add_alert(
        self,
        zone_id: str,
        alert_type: str,
        severity: str,
        title: str,
        description: str,
        issued_at: datetime,
        valid_until: Optional[datetime] = None
    ):
        """
        Ajoute une alerte active
        
        Args:
            zone_id: ID de la zone
            alert_type: Type d'alerte
            severity: Sévérité
            title: Titre
            description: Description
            issued_at: Date d'émission
            valid_until: Date d'expiration (optionnel)
        """
        zone = self.zones.get(zone_id)
        if not zone:
            return
        
        if zone.active_alerts is None:
            zone.active_alerts = []
        
        zone.active_alerts.append({
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "description": description,
            "issued_at": issued_at.isoformat(),
            "valid_until": valid_until.isoformat() if valid_until else None
        })
    
    def add_past_event(
        self,
        zone_id: str,
        event_type: str,
        date: datetime,
        title: str,
        description: str,
        impacts: Optional[Dict] = None
    ):
        """
        Ajoute un événement passé
        
        Args:
            zone_id: ID de la zone
            event_type: Type d'événement
            date: Date
            title: Titre
            description: Description
            impacts: Impacts (optionnel)
        """
        zone = self.zones.get(zone_id)
        if not zone:
            return
        
        if zone.past_events is None:
            zone.past_events = []
        
        zone.past_events.append({
            "event_type": event_type,
            "date": date.isoformat(),
            "title": title,
            "description": description,
            "impacts": impacts or {}
        })
    
    def calculate_distance_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calcule la distance entre deux points (formule de Haversine)
        
        Args:
            lat1, lon1: Coordonnées point 1
            lat2, lon2: Coordonnées point 2
        
        Returns:
            Distance en km
        """
        R = 6371  # Rayon terrestre en km
        
        # Convertir en radians
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)
        
        # Haversine
        a = (np.sin(delta_lat / 2) ** 2 +
             np.cos(lat1_rad) * np.cos(lat2_rad) *
             np.sin(delta_lon / 2) ** 2)
        
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c
    
    def find_nearest_zones(
        self,
        lat: float,
        lon: float,
        n: int = 5,
        zone_type: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Trouve les zones les plus proches d'un point
        
        Args:
            lat: Latitude
            lon: Longitude
            n: Nombre de zones à retourner
            zone_type: Filtrer par type (optionnel)
        
        Returns:
            Liste de (zone_id, distance_km)
        """
        distances = []
        
        for zone_id, zone in self.zones.items():
            # Filtrer par type si demandé
            if zone_type and zone.zone_type != zone_type:
                continue
            
            distance = self.calculate_distance_km(
                lat, lon,
                zone.center_lat, zone.center_lon
            )
            
            distances.append((zone_id, distance))
        
        # Trier par distance
        distances.sort(key=lambda x: x[1])
        
        return distances[:n]
    
    def get_zones_by_type(self, zone_type: str) -> List[ZoneInfo]:
        """
        Récupère les zones d'un type donné
        
        Args:
            zone_type: Type de zone
        
        Returns:
            Liste de ZoneInfo
        """
        return [
            zone for zone in self.zones.values()
            if zone.zone_type == zone_type
        ]
    
    def get_statistics(self) -> Dict:
        """Calcule des statistiques globales"""
        by_type = {}
        for zone_type in ['commune', 'bassin_versant', 'region']:
            zones = self.get_zones_by_type(zone_type)
            if zones:
                by_type[zone_type] = {
                    "count": len(zones),
                    "zones": [z.zone_name for z in zones]
                }
        
        total_area = sum(z.area_km2 for z in self.zones.values())
        total_population = sum(
            z.population for z in self.zones.values()
            if z.population
        )
        
        return {
            "total_zones": len(self.zones),
            "by_type": by_type,
            "total_area_km2": total_area,
            "formatted_area": format_area(total_area),
            "total_population": total_population,
            "formatted_population": format_population(total_population)
        }
    
    def __len__(self) -> int:
        return len(self.zones)
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"SpatialAnalyzer(zones={stats['total_zones']}, "
            f"area={stats['formatted_area']})"
        )