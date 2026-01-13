# core/module1/__init__.py
"""
Module 1 : Veille Hydrométéorologique et Climatique
Services avancés pour détection, prévision et alerte des risques climatiques
"""

__version__ = "1.0.0"

from .geolocation import GeolocationService
from .satellite import SatelliteService
from .hydro_models import (
    CurveNumberModel,
    HydrologicalAnalyzer,
    WatershedCharacteristics,
    estimate_time_of_concentration
)
from .ml_predictions import (
    DischargePredictor,
    RiskClassifier,
    create_features_from_weather
)
from .utils import (
    calculate_risk_level,
    format_coordinates,
    get_bbox_from_point,
    haversine_distance,
    get_risk_color,
    get_risk_label
)

__all__ = [
    'GeolocationService',
    'SatelliteService',
    'CurveNumberModel',
    'HydrologicalAnalyzer',
    'WatershedCharacteristics',
    'estimate_time_of_concentration',
    'DischargePredictor',
    'RiskClassifier',
    'create_features_from_weather',
    'calculate_risk_level',
    'format_coordinates',
    'get_bbox_from_point',
    'haversine_distance',
    'get_risk_color',
    'get_risk_label'
]