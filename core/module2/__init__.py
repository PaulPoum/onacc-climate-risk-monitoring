# core/module2/__init__.py
"""
Module 2 : Cartes de risques et catastrophes climatiques (SIG)
===============================================================

Système d'Information Géographique pour la visualisation spatiale
des risques climatiques (inondations, sécheresses, multi-risques).

Composants :
- risk_mapper.py : Cartographie des zones à risque
- flood_zones.py : Zones inondables et plaines alluviales
- drought_zones.py : Zones en déficit pluviométrique/sécheresse
- multi_risk.py : Analyse multi-risques et superposition
- filters.py : Filtres temporels et thématiques
- zone_info.py : Fiches détaillées par zone
- utils.py : Utilitaires cartographiques

Auteur: ONACC Team
Version: 2.0.0
"""

from core.module2.risk_mapper import RiskMapper, RiskType, RiskLayer
from core.module2.flood_zones import FloodZoneAnalyzer, FloodRiskLevel
from core.module2.drought_zones import DroughtZoneAnalyzer, DroughtSeverity
from core.module2.multi_risk import MultiRiskAnalyzer
from core.module2.filters import (
    TemporalFilter,
    TemporalPeriod,
    RiskFilter,
    AlertLevelFilter,
    AlertLevel,
    CompositeFilter
)
from core.module2.zone_info import (
    ZoneInfoProvider,
    ZoneDetails,
    ZoneType,
    ClimateIndices,
    ActiveAlert,
    HistoricalEvent
)
from core.module2.utils import (
    create_risk_color_scale,
    get_risk_level_label,
    format_area
)

__all__ = [
    # Core classes
    'RiskMapper',
    'RiskType',
    'RiskLayer',
    'FloodZoneAnalyzer',
    'FloodRiskLevel',
    'DroughtZoneAnalyzer',
    'DroughtSeverity',
    'MultiRiskAnalyzer',
    
    # Filters
    'TemporalFilter',
    'TemporalPeriod',
    'RiskFilter',
    'AlertLevelFilter',
    'AlertLevel',
    'CompositeFilter',
    
    # Zone info
    'ZoneInfoProvider',
    'ZoneDetails',
    'ZoneType',
    'ClimateIndices',
    'ActiveAlert',
    'HistoricalEvent',
    
    # Utils
    'create_risk_color_scale',
    'get_risk_level_label',
    'format_area'
]

__version__ = '2.0.0'