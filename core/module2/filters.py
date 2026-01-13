# core/module2/filters.py
"""
Module 2 - Filtres cartographiques
===================================

Système de filtrage pour la visualisation cartographique :
- Filtres temporels (jour, décade, mois, saison, année)
- Filtres par type de risque
- Filtres par niveau d'alerte
"""

from typing import List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from enum import Enum


class TemporalPeriod(Enum):
    """Périodes temporelles prédéfinies"""
    TODAY = "today"
    YESTERDAY = "yesterday"
    WEEK = "week"
    DECADE = "decade"  # 10 jours
    MONTH = "month"
    QUARTER = "quarter"
    SEASON = "season"
    YEAR = "year"
    CUSTOM = "custom"


class AlertLevel(Enum):
    """Niveaux d'alerte"""
    GREEN = "green"  # Normal
    YELLOW = "yellow"  # Vigilance
    ORANGE = "orange"  # Alerte
    RED = "red"  # Alerte renforcée
    EXTREME = "extreme"  # Alerte maximale


@dataclass
class TemporalFilter:
    """
    Filtre temporel pour les données cartographiques
    
    Attributes:
        period: Période prédéfinie
        start_date: Date de début (si CUSTOM)
        end_date: Date de fin (si CUSTOM)
        include_forecast: Inclure les prévisions
    """
    period: TemporalPeriod
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    include_forecast: bool = False
    
    def get_date_range(self) -> Tuple[datetime, datetime]:
        """
        Calcule la plage de dates en fonction de la période
        
        Returns:
            (start_datetime, end_datetime)
        """
        now = datetime.now()
        today = date.today()
        
        if self.period == TemporalPeriod.TODAY:
            start = datetime.combine(today, datetime.min.time())
            end = datetime.combine(today, datetime.max.time())
        
        elif self.period == TemporalPeriod.YESTERDAY:
            yesterday = today - timedelta(days=1)
            start = datetime.combine(yesterday, datetime.min.time())
            end = datetime.combine(yesterday, datetime.max.time())
        
        elif self.period == TemporalPeriod.WEEK:
            start = datetime.combine(today - timedelta(days=7), datetime.min.time())
            end = now
        
        elif self.period == TemporalPeriod.DECADE:
            start = datetime.combine(today - timedelta(days=10), datetime.min.time())
            end = now
        
        elif self.period == TemporalPeriod.MONTH:
            start = datetime.combine(today - timedelta(days=30), datetime.min.time())
            end = now
        
        elif self.period == TemporalPeriod.QUARTER:
            start = datetime.combine(today - timedelta(days=90), datetime.min.time())
            end = now
        
        elif self.period == TemporalPeriod.SEASON:
            # Saison = ~6 mois
            start = datetime.combine(today - timedelta(days=180), datetime.min.time())
            end = now
        
        elif self.period == TemporalPeriod.YEAR:
            start = datetime.combine(today - timedelta(days=365), datetime.min.time())
            end = now
        
        elif self.period == TemporalPeriod.CUSTOM:
            if not self.start_date or not self.end_date:
                raise ValueError("Dates start_date et end_date requises pour période CUSTOM")
            
            start = datetime.combine(self.start_date, datetime.min.time())
            end = datetime.combine(self.end_date, datetime.max.time())
        
        else:
            raise ValueError(f"Période non supportée : {self.period}")
        
        return start, end
    
    def get_period_label(self) -> str:
        """
        Retourne le label de la période
        
        Returns:
            Label lisible
        """
        labels = {
            TemporalPeriod.TODAY: "Aujourd'hui",
            TemporalPeriod.YESTERDAY: "Hier",
            TemporalPeriod.WEEK: "7 derniers jours",
            TemporalPeriod.DECADE: "10 derniers jours",
            TemporalPeriod.MONTH: "30 derniers jours",
            TemporalPeriod.QUARTER: "3 derniers mois",
            TemporalPeriod.SEASON: "Saison en cours",
            TemporalPeriod.YEAR: "Dernière année",
        }
        
        if self.period == TemporalPeriod.CUSTOM:
            if self.start_date and self.end_date:
                return f"{self.start_date.strftime('%d/%m/%Y')} - {self.end_date.strftime('%d/%m/%Y')}"
            return "Période personnalisée"
        
        return labels.get(self.period, str(self.period.value))


@dataclass
class RiskFilter:
    """
    Filtre par type de risque
    
    Attributes:
        risk_types: Types de risques à inclure
        exclude_types: Types de risques à exclure (optionnel)
    """
    risk_types: Set[str]
    exclude_types: Optional[Set[str]] = None
    
    def is_included(self, risk_type: str) -> bool:
        """
        Vérifie si un type de risque est inclus
        
        Args:
            risk_type: Type de risque à vérifier
        
        Returns:
            True si inclus, False sinon
        """
        # Vérifier exclusions
        if self.exclude_types and risk_type in self.exclude_types:
            return False
        
        # Vérifier inclusions
        if not self.risk_types or risk_type in self.risk_types:
            return True
        
        return False
    
    @classmethod
    def all_risks(cls) -> 'RiskFilter':
        """Filtre incluant tous les risques"""
        return cls(risk_types=set())
    
    @classmethod
    def flood_only(cls) -> 'RiskFilter':
        """Filtre uniquement inondations"""
        return cls(risk_types={'flood'})
    
    @classmethod
    def drought_only(cls) -> 'RiskFilter':
        """Filtre uniquement sécheresse"""
        return cls(risk_types={'drought'})
    
    @classmethod
    def critical_risks(cls) -> 'RiskFilter':
        """Filtre risques majeurs (inondations, sécheresse, tempêtes)"""
        return cls(risk_types={'flood', 'drought', 'storm'})


@dataclass
class AlertLevelFilter:
    """
    Filtre par niveau d'alerte
    
    Attributes:
        levels: Niveaux d'alerte à inclure
        min_level: Niveau minimum (optionnel)
    """
    levels: Set[AlertLevel]
    min_level: Optional[AlertLevel] = None
    
    def is_included(self, level: str) -> bool:
        """
        Vérifie si un niveau d'alerte est inclus
        
        Args:
            level: Niveau d'alerte à vérifier
        
        Returns:
            True si inclus, False sinon
        """
        # Mapping string -> AlertLevel
        level_map = {
            'low': AlertLevel.GREEN,
            'moderate': AlertLevel.YELLOW,
            'high': AlertLevel.ORANGE,
            'critical': AlertLevel.RED,
            'extreme': AlertLevel.EXTREME,
            'exceptional': AlertLevel.EXTREME
        }
        
        alert_level = level_map.get(level.lower())
        
        if not alert_level:
            return False
        
        # Vérifier niveau minimum
        if self.min_level:
            level_priority = {
                AlertLevel.GREEN: 0,
                AlertLevel.YELLOW: 1,
                AlertLevel.ORANGE: 2,
                AlertLevel.RED: 3,
                AlertLevel.EXTREME: 4
            }
            
            if level_priority[alert_level] < level_priority[self.min_level]:
                return False
        
        # Vérifier si dans la liste
        if self.levels and alert_level not in self.levels:
            return False
        
        return True
    
    @classmethod
    def all_levels(cls) -> 'AlertLevelFilter':
        """Filtre incluant tous les niveaux"""
        return cls(levels=set())
    
    @classmethod
    def critical_only(cls) -> 'AlertLevelFilter':
        """Filtre uniquement niveaux critiques"""
        return cls(
            levels={AlertLevel.RED, AlertLevel.EXTREME},
            min_level=AlertLevel.RED
        )
    
    @classmethod
    def warnings_and_above(cls) -> 'AlertLevelFilter':
        """Filtre niveaux d'alerte et supérieurs"""
        return cls(
            levels={AlertLevel.ORANGE, AlertLevel.RED, AlertLevel.EXTREME},
            min_level=AlertLevel.ORANGE
        )


@dataclass
class CompositeFilter:
    """
    Filtre composite combinant tous les critères
    
    Attributes:
        temporal: Filtre temporel
        risk: Filtre par type de risque
        alert_level: Filtre par niveau d'alerte
        spatial_bbox: Bounding box géographique (optionnel)
    """
    temporal: TemporalFilter
    risk: RiskFilter
    alert_level: AlertLevelFilter
    spatial_bbox: Optional[Tuple[float, float, float, float]] = None
    
    def apply(self, layers: List) -> List:
        """
        Applique tous les filtres à une liste de couches
        
        Args:
            layers: Liste des couches à filtrer
        
        Returns:
            Couches filtrées
        """
        filtered = layers
        
        # Filtre temporel
        start_date, end_date = self.temporal.get_date_range()
        filtered = [
            layer for layer in filtered
            if hasattr(layer, 'timestamp') and 
               start_date <= layer.timestamp <= end_date
        ]
        
        # Filtre par type de risque
        filtered = [
            layer for layer in filtered
            if hasattr(layer, 'risk_type') and 
               self.risk.is_included(layer.risk_type.value if hasattr(layer.risk_type, 'value') else str(layer.risk_type))
        ]
        
        # Filtre par niveau d'alerte
        filtered = [
            layer for layer in filtered
            if hasattr(layer, 'level') and 
               self.alert_level.is_included(layer.level)
        ]
        
        # Filtre spatial (bbox)
        if self.spatial_bbox:
            min_lon, min_lat, max_lon, max_lat = self.spatial_bbox
            
            filtered = [
                layer for layer in filtered
                if hasattr(layer, 'properties') and
                   layer.properties.get('center_lat') and
                   layer.properties.get('center_lon') and
                   (min_lon <= layer.properties['center_lon'] <= max_lon) and
                   (min_lat <= layer.properties['center_lat'] <= max_lat)
            ]
        
        return filtered
    
    def get_summary(self) -> dict:
        """
        Résumé des critères de filtrage
        
        Returns:
            Dictionnaire descriptif
        """
        return {
            'temporal_period': self.temporal.get_period_label(),
            'risk_types': list(self.risk.risk_types) if self.risk.risk_types else ['all'],
            'alert_levels': [level.value for level in self.alert_level.levels] if self.alert_level.levels else ['all'],
            'spatial_filter': 'bbox' if self.spatial_bbox else 'none',
            'include_forecast': self.temporal.include_forecast
        }