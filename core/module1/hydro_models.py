"""
Modèles hydrologiques pour prévision des débits et risques de crue
Implémentation Curve Number (SCS-CN) et analyse hydrologique
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

class CurveNumberModel:
    """
    Modèle Curve Number (SCS-CN) du Soil Conservation Service
    
    Modèle pluie-débit empirique largement utilisé pour estimer le ruissellement
    à partir des précipitations, du type de sol et de l'occupation du sol.
    
    Reference:
    - USDA-SCS (1972) National Engineering Handbook, Section 4: Hydrology
    """
    
    def __init__(self, curve_number: float = 75):
        """
        Initialise le modèle Curve Number
        
        Args:
            curve_number: CN (30-100)
                - 30-50: Forêt dense, sols perméables
                - 50-70: Terres agricoles, perméabilité moyenne
                - 70-85: Zones urbaines, faible perméabilité
                - 85-100: Surfaces imperméables (routes, toits)
        
        CN typiques au Cameroun:
        - Forêt équatoriale: 55-65
        - Savane: 65-75
        - Zones agricoles: 70-80
        - Zones urbaines: 80-90
        """
        if not 30 <= curve_number <= 100:
            raise ValueError("Curve Number doit être entre 30 et 100")
        
        self.CN = curve_number
        
        # Calcul rétention maximale (inches)
        # S = (1000/CN) - 10
        self.S = (1000 / self.CN) - 10
        
        # Paramètres calibrés
        self.initial_abstraction_ratio = 0.2  # λ = 0.2 (standard)
    
    def calculate_runoff(
        self,
        precipitation_mm: np.ndarray,
        initial_abstraction_ratio: Optional[float] = None
    ) -> np.ndarray:
        """
        Calcule le ruissellement à partir des précipitations
        
        Équation SCS-CN:
        Q = ((P - Ia)²) / (P - Ia + S)  si P > Ia
        Q = 0                           si P <= Ia
        
        où:
        - Q = Ruissellement (runoff)
        - P = Précipitation
        - Ia = Pertes initiales = λ * S
        - S = Rétention maximale
        - λ = Ratio pertes initiales (défaut 0.2)
        
        Args:
            precipitation_mm: Précipitations journalières (mm)
            initial_abstraction_ratio: Ratio λ (défaut 0.2)
        
        Returns:
            Ruissellement en mm
        """
        
        if initial_abstraction_ratio is None:
            initial_abstraction_ratio = self.initial_abstraction_ratio
        
        # Convertir mm en inches (1 inch = 25.4 mm)
        P_inches = precipitation_mm / 25.4
        
        # Pertes initiales (initial abstraction)
        Ia = initial_abstraction_ratio * self.S
        
        # Calcul ruissellement (inches)
        runoff_inches = np.zeros_like(P_inches)
        
        # Appliquer équation SCS-CN seulement si P > Ia
        mask = P_inches > Ia
        P_effective = P_inches[mask] - Ia
        
        runoff_inches[mask] = (P_effective ** 2) / (P_effective + self.S)
        
        # Reconvertir en mm
        runoff_mm = runoff_inches * 25.4
        
        return runoff_mm
    
    def calculate_peak_discharge(
        self,
        runoff_mm: float,
        watershed_area_km2: float,
        time_of_concentration_hours: float
    ) -> float:
        """
        Calcule le débit de pointe avec la méthode rationnelle
        
        Q_peak = C * I * A
        
        Args:
            runoff_mm: Ruissellement total (mm)
            watershed_area_km2: Surface du bassin versant (km²)
            time_of_concentration_hours: Temps de concentration (h)
        
        Returns:
            Débit de pointe (m³/s)
        """
        
        # Coefficient de ruissellement
        C = min(runoff_mm / 100, 0.95)  # Max 0.95
        
        # Intensité moyenne (mm/h)
        I = runoff_mm / time_of_concentration_hours
        
        # Surface en hectares
        A_ha = watershed_area_km2 * 100
        
        # Débit de pointe (m³/s)
        # Q = C * I * A / 360
        Q_peak = (C * I * A_ha) / 360
        
        return Q_peak


class HydrologicalAnalyzer:
    """
    Analyseur hydrologique pour prévision des crues et calcul des risques
    """
    
    def __init__(
        self,
        curve_number: float = 75,
        watershed_area_km2: float = 100,
        time_of_concentration_hours: float = 6
    ):
        """
        Initialise l'analyseur hydrologique
        
        Args:
            curve_number: CN du bassin (30-100)
            watershed_area_km2: Surface du bassin versant
            time_of_concentration_hours: Temps de concentration
        """
        self.cn_model = CurveNumberModel(curve_number)
        self.watershed_area_km2 = watershed_area_km2
        self.time_of_concentration = time_of_concentration_hours
    
    def forecast_discharge(
        self,
        precipitation: np.ndarray,
        dates: Optional[pd.DatetimeIndex] = None
    ) -> Dict:
        """
        Prévoit le débit d'une rivière
        
        Args:
            precipitation: Précipitations prévues (mm/jour)
            dates: Dates correspondantes (optionnel)
        
        Returns:
            Dict avec débit, ruissellement, et analyse de risque
        """
        
        if dates is None:
            dates = pd.date_range(
                start=datetime.now(),
                periods=len(precipitation),
                freq='D'
            )
        
        # Calculer ruissellement
        runoff = self.cn_model.calculate_runoff(precipitation)
        
        # Convertir en débit (m³/s)
        # Formule simplifiée: Q = (Runoff_mm * Area_km2 * 1000) / (86400 s/jour)
        discharge_m3s = (runoff * self.watershed_area_km2 * 1000) / 86400
        
        # Débit de pointe pour chaque jour
        peak_discharges = np.array([
            self.cn_model.calculate_peak_discharge(
                r,
                self.watershed_area_km2,
                self.time_of_concentration
            ) if r > 0 else 0
            for r in runoff
        ])
        
        # Analyser risque
        risk_analysis = self._analyze_flood_risk(
            discharge_m3s,
            peak_discharges,
            dates
        )
        
        return {
            'dates': dates,
            'precipitation_mm': precipitation,
            'runoff_mm': runoff,
            'discharge_m3s': discharge_m3s,
            'peak_discharge_m3s': peak_discharges,
            'mean_discharge': np.mean(discharge_m3s),
            'max_discharge': np.max(discharge_m3s),
            'total_volume_m3': np.sum(discharge_m3s) * 86400,
            'risk_analysis': risk_analysis
        }
    
    def _analyze_flood_risk(
        self,
        discharge: np.ndarray,
        peak_discharge: np.ndarray,
        dates: pd.DatetimeIndex
    ) -> Dict:
        """
        Analyse le risque de crue
        
        Seuils basés sur analyse statistique et expertise hydrologique
        """
        
        Q_mean = np.mean(discharge)
        Q_max = np.max(discharge)
        Q_peak_max = np.max(peak_discharge)
        
        # Seuils de crue (multiples du débit moyen)
        threshold_moderate = Q_mean * 2
        threshold_high = Q_mean * 5
        threshold_critical = Q_mean * 10
        
        # Classification du risque
        if Q_max >= threshold_critical or Q_peak_max >= threshold_critical:
            risk_level = 'critical'
            risk_description = 'Risque de crue majeure - Évacuation recommandée'
        elif Q_max >= threshold_high or Q_peak_max >= threshold_high:
            risk_level = 'high'
            risk_description = 'Risque élevé de crue - Surveillance renforcée'
        elif Q_max >= threshold_moderate or Q_peak_max >= threshold_moderate:
            risk_level = 'moderate'
            risk_description = 'Risque modéré de crue - Vigilance'
        else:
            risk_level = 'low'
            risk_description = 'Risque faible - Situation normale'
        
        # Identifier jours critiques
        critical_days = []
        for i, (d, q, qp) in enumerate(zip(dates, discharge, peak_discharge)):
            if q >= threshold_high or qp >= threshold_high:
                critical_days.append({
                    'date': d,
                    'day_index': i,
                    'discharge': q,
                    'peak_discharge': qp,
                    'severity': 'critical' if q >= threshold_critical else 'high'
                })
        
        # Statistiques de retour (approximation)
        # Période de retour approximative basée sur le ratio Q_max / Q_mean
        ratio = Q_max / Q_mean if Q_mean > 0 else 1
        
        if ratio >= 20:
            return_period_years = 100
        elif ratio >= 10:
            return_period_years = 50
        elif ratio >= 5:
            return_period_years = 20
        elif ratio >= 2:
            return_period_years = 5
        else:
            return_period_years = 2
        
        return {
            'risk_level': risk_level,
            'risk_description': risk_description,
            'Q_mean': Q_mean,
            'Q_max': Q_max,
            'Q_peak_max': Q_peak_max,
            'thresholds': {
                'moderate': threshold_moderate,
                'high': threshold_high,
                'critical': threshold_critical
            },
            'critical_days': critical_days,
            'n_critical_days': len(critical_days),
            'return_period_years': return_period_years,
            'peak_day': int(np.argmax(discharge))
        }
    
    def calculate_flood_volume(
        self,
        discharge: np.ndarray,
        threshold_discharge: float
    ) -> Dict:
        """
        Calcule le volume d'eau excédentaire (crue)
        
        Args:
            discharge: Série de débits (m³/s)
            threshold_discharge: Débit seuil de débordement (m³/s)
        
        Returns:
            Volume de crue et statistiques
        """
        
        # Débit excédentaire
        excess_discharge = np.maximum(discharge - threshold_discharge, 0)
        
        # Volume (m³)
        # Q (m³/s) * 86400 (s/jour) = volume journalier
        excess_volume_m3 = np.sum(excess_discharge) * 86400
        
        # Durée de crue (jours)
        flood_days = np.sum(excess_discharge > 0)
        
        # Débit de pointe excédentaire
        peak_excess = np.max(excess_discharge)
        
        return {
            'excess_volume_m3': excess_volume_m3,
            'excess_volume_million_m3': excess_volume_m3 / 1_000_000,
            'flood_duration_days': flood_days,
            'peak_excess_discharge': peak_excess,
            'mean_excess_discharge': np.mean(excess_discharge[excess_discharge > 0]) if flood_days > 0 else 0
        }
    
    def estimate_affected_area(
        self,
        excess_volume_m3: float,
        flood_depth_m: float = 1.0
    ) -> Dict:
        """
        Estime la surface inondée
        
        Args:
            excess_volume_m3: Volume d'eau excédentaire (m³)
            flood_depth_m: Profondeur moyenne d'inondation (m)
        
        Returns:
            Surface affectée et statistiques
        """
        
        # Surface inondée (m²)
        flooded_area_m2 = excess_volume_m3 / flood_depth_m
        flooded_area_km2 = flooded_area_m2 / 1_000_000
        flooded_area_ha = flooded_area_m2 / 10_000
        
        # Population potentiellement affectée (estimation)
        # Hypothèse: densité moyenne 50 personnes/km²
        density_per_km2 = 50
        affected_population = int(flooded_area_km2 * density_per_km2)
        
        return {
            'flooded_area_m2': flooded_area_m2,
            'flooded_area_km2': flooded_area_km2,
            'flooded_area_ha': flooded_area_ha,
            'flood_depth_m': flood_depth_m,
            'affected_population_estimate': affected_population
        }


class WatershedCharacteristics:
    """
    Caractéristiques des bassins versants du Cameroun
    """
    
    # Bassins versants principaux
    WATERSHEDS = {
        'sanaga': {
            'name': 'Sanaga',
            'area_km2': 133000,
            'cn': 72,  # Forêt équatoriale + agriculture
            'time_concentration_h': 48,
            'regions': ['Centre', 'Sud', 'Littoral']
        },
        'benoue': {
            'name': 'Bénoué',
            'area_km2': 65000,
            'cn': 78,  # Savane + agriculture intensive
            'time_concentration_h': 36,
            'regions': ['Nord', 'Adamaoua']
        },
        'logone': {
            'name': 'Logone',
            'area_km2': 85000,
            'cn': 75,  # Savane sahélienne
            'time_concentration_h': 40,
            'regions': ['Extrême-Nord']
        },
        'nyong': {
            'name': 'Nyong',
            'area_km2': 27800,
            'cn': 70,  # Forêt dense
            'time_concentration_h': 24,
            'regions': ['Centre', 'Sud']
        },
        'wouri': {
            'name': 'Wouri',
            'area_km2': 8800,
            'cn': 82,  # Zone urbaine Douala
            'time_concentration_h': 12,
            'regions': ['Littoral']
        }
    }
    
    @classmethod
    def get_watershed_for_region(cls, region: str) -> Dict:
        """
        Retourne le bassin versant principal pour une région
        
        Args:
            region: Nom de la région
        
        Returns:
            Caractéristiques du bassin versant
        """
        
        for watershed_id, data in cls.WATERSHEDS.items():
            if region in data['regions']:
                return {
                    'id': watershed_id,
                    **data
                }
        
        # Par défaut : paramètres moyens
        return {
            'id': 'default',
            'name': 'Bassin local',
            'area_km2': 100,
            'cn': 75,
            'time_concentration_h': 6,
            'regions': [region]
        }
    
    @classmethod
    def create_analyzer_for_region(cls, region: str) -> HydrologicalAnalyzer:
        """
        Crée un analyseur hydrologique adapté à la région
        
        Args:
            region: Nom de la région
        
        Returns:
            HydrologicalAnalyzer configuré
        """
        
        watershed = cls.get_watershed_for_region(region)
        
        return HydrologicalAnalyzer(
            curve_number=watershed['cn'],
            watershed_area_km2=watershed['area_km2'],
            time_of_concentration_hours=watershed['time_concentration_h']
        )


def estimate_time_of_concentration(
    length_km: float,
    slope_percent: float,
    method: str = 'kirpich'
) -> float:
    """
    Estime le temps de concentration d'un bassin versant
    
    Args:
        length_km: Longueur du cours d'eau principal (km)
        slope_percent: Pente moyenne (%)
        method: Méthode de calcul ('kirpich', 'bransby-williams')
    
    Returns:
        Temps de concentration (heures)
    """
    
    length_m = length_km * 1000
    slope_ratio = slope_percent / 100
    
    if method == 'kirpich':
        # Formule de Kirpich (bassins < 80 ha)
        # Tc = 0.0195 * L^0.77 * S^-0.385
        # L en mètres, S en m/m
        tc_minutes = 0.0195 * (length_m ** 0.77) * (slope_ratio ** -0.385)
        return tc_minutes / 60
    
    elif method == 'bransby-williams':
        # Formule de Bransby-Williams (grands bassins)
        # Tc = 14.6 * L / (A^0.1 * S^0.2)
        # Approximation si surface non disponible
        tc_hours = 0.06 * length_km / (slope_ratio ** 0.2)
        return tc_hours
    
    else:
        raise ValueError(f"Méthode inconnue: {method}")