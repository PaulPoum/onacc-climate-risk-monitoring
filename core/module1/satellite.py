# core/module1/satellite.py
"""
Service d'imagerie satellite pour détection inondations et sécheresse
Support multi-sources : Mapbox, NASA GIBS, Sentinel Hub
"""
import streamlit as st
import numpy as np
import requests
from typing import Tuple, Dict, Optional, List
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO
import base64

class SatelliteService:
    """
    Service d'imagerie satellite multi-sources avec détection automatique
    """
    
    def __init__(self):
        # Configuration APIs gratuites
        self.mapbox_token = st.secrets.get("MAPBOX_TOKEN", "")
        self.nasa_gibs_url = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
        
        # Paramètres cache
        self.cache_ttl = 86400  # 24 heures
        
        # Statistiques usage
        if 'satellite_stats' not in st.session_state:
            st.session_state['satellite_stats'] = {
                'mapbox_calls': 0,
                'nasa_calls': 0,
                'cache_hits': 0
            }
    
    def get_satellite_image(
        self,
        lat: float,
        lon: float,
        zoom: int = 10,
        width: int = 512,
        height: int = 512,
        source: str = 'auto'
    ) -> Optional[Dict]:
        """
        Récupère une image satellite (méthode unifiée)
        
        Args:
            lat, lon: Coordonnées centre
            zoom: Niveau de zoom (0-22)
            width, height: Dimensions image
            source: 'mapbox' | 'nasa' | 'auto'
        
        Returns:
            Dict {
                'image': np.ndarray,
                'source': str,
                'timestamp': str,
                'metadata': dict
            }
        """
        
        # Clé cache
        cache_key = f"sat_{lat}_{lon}_{zoom}_{width}_{height}_{source}"
        
        # Vérifier cache
        if cache_key in st.session_state:
            st.session_state['satellite_stats']['cache_hits'] += 1
            return st.session_state[cache_key]
        
        result = None
        
        # Essayer sources selon priorité
        if source == 'auto' or source == 'mapbox':
            if self.mapbox_token:
                result = self._get_mapbox_image(lat, lon, zoom, width, height)
                if result:
                    result['source'] = 'mapbox'
        
        if result is None and (source == 'auto' or source == 'nasa'):
            bbox = self._calculate_bbox(lat, lon, zoom, width, height)
            result = self._get_nasa_gibs_image(bbox, width, height)
            if result:
                result['source'] = 'nasa'
        
        # Mettre en cache
        if result:
            st.session_state[cache_key] = result
        
        return result
    
    @st.cache_data(ttl=86400)
    def _get_mapbox_image(
        _self,
        lat: float,
        lon: float,
        zoom: int,
        width: int,
        height: int
    ) -> Optional[Dict]:
        """
        Récupère image via Mapbox Static Images API
        
        Gratuit jusqu'à 50,000 requêtes/mois
        """
        
        if not _self.mapbox_token:
            return None
        
        try:
            # Mapbox Static Images API
            url = (
                f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
                f"{lon},{lat},{zoom}/{width}x{height}@2x"
                f"?access_token={_self.mapbox_token}"
            )
            
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                
                st.session_state['satellite_stats']['mapbox_calls'] += 1
                
                return {
                    'image': np.array(img),
                    'timestamp': datetime.now().isoformat(),
                    'metadata': {
                        'center': [lat, lon],
                        'zoom': zoom,
                        'dimensions': [width, height],
                        'style': 'satellite-v9'
                    }
                }
            else:
                st.warning(f"⚠️ Mapbox erreur {response.status_code}")
        
        except Exception as e:
            st.warning(f"⚠️ Erreur Mapbox: {e}")
        
        return None
    
    @st.cache_data(ttl=86400)
    def _get_nasa_gibs_image(
        _self,
        bbox: Tuple[float, float, float, float],
        width: int,
        height: int,
        date: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Récupère image via NASA GIBS (MODIS)
        
        Gratuit, illimité
        """
        
        if date is None:
            # Hier (MODIS a 1 jour de latence)
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        try:
            # WMS GetMap request
            params = {
                'SERVICE': 'WMS',
                'REQUEST': 'GetMap',
                'VERSION': '1.3.0',
                'LAYERS': 'MODIS_Terra_CorrectedReflectance_TrueColor',
                'FORMAT': 'image/jpeg',
                'WIDTH': width,
                'HEIGHT': height,
                'CRS': 'EPSG:4326',
                'BBOX': f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}",  # lat,lon order for EPSG:4326
                'TIME': date
            }
            
            response = requests.get(_self.nasa_gibs_url, params=params, timeout=20)
            
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                
                st.session_state['satellite_stats']['nasa_calls'] += 1
                
                return {
                    'image': np.array(img),
                    'timestamp': date,
                    'metadata': {
                        'bbox': bbox,
                        'dimensions': [width, height],
                        'satellite': 'MODIS Terra',
                        'resolution': '250m'
                    }
                }
        
        except Exception as e:
            st.warning(f"⚠️ Erreur NASA GIBS: {e}")
        
        return None
    
    def detect_water_bodies(
        self,
        rgb_image: np.ndarray,
        method: str = 'rgb_threshold'
    ) -> Tuple[np.ndarray, float, Dict]:
        """
        Détecte les corps d'eau dans une image satellite
        
        Args:
            rgb_image: Image RGB (H, W, 3)
            method: 'rgb_threshold' | 'ndwi' (future)
        
        Returns:
            (water_mask, water_percentage, stats)
        """
        
        if method == 'rgb_threshold':
            return self._detect_water_rgb_threshold(rgb_image)
        else:
            return self._detect_water_rgb_threshold(rgb_image)
    
    def _detect_water_rgb_threshold(
        self,
        rgb_image: np.ndarray
    ) -> Tuple[np.ndarray, float, Dict]:
        """
        Détection d'eau par seuillage RGB simple
        
        Principe : Eau apparaît plus bleue (B > R et B > G)
        """
        
        # Normaliser 0-1
        img = rgb_image.astype(float) / 255.0
        
        # Masque eau : Bleu dominant
        water_mask = (
            (img[:, :, 2] > img[:, :, 0] * 1.2) &  # B > R * 1.2
            (img[:, :, 2] > img[:, :, 1] * 1.1) &  # B > G * 1.1
            (img[:, :, 2] > 0.25)                   # B > seuil minimum
        )
        
        # Filtrer bruit (morphologie)
        from scipy import ndimage
        
        # Opérations morphologiques
        water_mask = ndimage.binary_opening(water_mask, iterations=2)
        water_mask = ndimage.binary_closing(water_mask, iterations=2)
        
        # Statistiques
        n_pixels = water_mask.size
        n_water_pixels = np.sum(water_mask)
        water_percentage = (n_water_pixels / n_pixels) * 100
        
        # Label composantes connexes
        labeled, n_features = ndimage.label(water_mask)
        
        # Taille zones d'eau
        water_bodies = []
        for i in range(1, n_features + 1):
            size = np.sum(labeled == i)
            if size > 100:  # Filtrer petites zones (bruit)
                water_bodies.append(size)
        
        stats = {
            'total_pixels': n_pixels,
            'water_pixels': n_water_pixels,
            'water_percentage': water_percentage,
            'n_water_bodies': len(water_bodies),
            'largest_water_body': max(water_bodies) if water_bodies else 0,
            'avg_water_body_size': np.mean(water_bodies) if water_bodies else 0
        }
        
        return water_mask, water_percentage, stats
    
    def calculate_ndvi(
        self,
        nir: np.ndarray,
        red: np.ndarray
    ) -> Tuple[np.ndarray, Dict]:
        """
        Calcule NDVI (Normalized Difference Vegetation Index)
        
        NDVI = (NIR - RED) / (NIR + RED)
        
        Indicateur de santé végétation (sécheresse)
        
        Args:
            nir: Bande proche infrarouge
            red: Bande rouge
        
        Returns:
            (ndvi_array, stats)
        """
        
        # Éviter division par zéro
        denominator = nir + red
        denominator = np.where(denominator == 0, 0.0001, denominator)
        
        ndvi = (nir - red) / denominator
        
        # Clamp [-1, 1]
        ndvi = np.clip(ndvi, -1, 1)
        
        # Statistiques
        stats = {
            'mean': float(np.mean(ndvi)),
            'std': float(np.std(ndvi)),
            'min': float(np.min(ndvi)),
            'max': float(np.max(ndvi)),
            'median': float(np.median(ndvi)),
            # Classification
            'bare_soil': float(np.sum((ndvi >= -1) & (ndvi < 0.1)) / ndvi.size * 100),
            'sparse_vegetation': float(np.sum((ndvi >= 0.1) & (ndvi < 0.3)) / ndvi.size * 100),
            'moderate_vegetation': float(np.sum((ndvi >= 0.3) & (ndvi < 0.6)) / ndvi.size * 100),
            'dense_vegetation': float(np.sum(ndvi >= 0.6) / ndvi.size * 100)
        }
        
        return ndvi, stats
    
    def create_overlay_image(
        self,
        base_image: np.ndarray,
        mask: np.ndarray,
        color: Tuple[int, int, int] = (0, 100, 255),
        alpha: float = 0.5
    ) -> np.ndarray:
        """
        Crée une image avec overlay coloré sur masque
        
        Args:
            base_image: Image de base RGB
            mask: Masque binaire (True/False)
            color: Couleur RGB de l'overlay
            alpha: Transparence (0=transparent, 1=opaque)
        
        Returns:
            Image avec overlay
        """
        
        result = base_image.copy()
        
        # Créer overlay
        overlay = np.zeros_like(result)
        overlay[mask] = color
        
        # Blend avec transparence
        result = (result * (1 - alpha) + overlay * alpha).astype(np.uint8)
        
        return result
    
    def create_heatmap(
        self,
        data: np.ndarray,
        colormap: str = 'RdYlGn'
    ) -> np.ndarray:
        """
        Crée une heatmap colorée à partir de données
        
        Args:
            data: Array 2D de valeurs (ex: NDVI)
            colormap: Nom du colormap matplotlib
        
        Returns:
            Image RGB
        """
        
        import matplotlib.pyplot as plt
        from matplotlib import cm
        
        # Normaliser 0-1
        data_normalized = (data - data.min()) / (data.max() - data.min() + 1e-8)
        
        # Appliquer colormap
        cmap = cm.get_cmap(colormap)
        colored = cmap(data_normalized)
        
        # Convertir en RGB uint8
        rgb = (colored[:, :, :3] * 255).astype(np.uint8)
        
        return rgb
    
    def calculate_affected_area(
        self,
        mask: np.ndarray,
        pixel_size_m: float,
        bbox: Tuple[float, float, float, float]
    ) -> Dict:
        """
        Calcule la surface réelle affectée à partir d'un masque
        
        Args:
            mask: Masque binaire
            pixel_size_m: Taille d'un pixel en mètres
            bbox: Bounding box (pour calcul précis)
        
        Returns:
            Dict avec surface en m² et km²
        """
        
        from core.module1.utils import haversine_distance
        
        # Calculer taille réelle bbox
        min_lon, min_lat, max_lon, max_lat = bbox
        
        width_km = haversine_distance(min_lat, min_lon, min_lat, max_lon)
        height_km = haversine_distance(min_lat, min_lon, max_lat, min_lon)
        
        # Surface totale
        total_area_km2 = width_km * height_km
        total_area_m2 = total_area_km2 * 1_000_000
        
        # Pixels totaux
        total_pixels = mask.size
        affected_pixels = np.sum(mask)
        
        # Pourcentage
        percentage = (affected_pixels / total_pixels) * 100
        
        # Surface affectée
        affected_area_m2 = (affected_pixels / total_pixels) * total_area_m2
        affected_area_km2 = affected_area_m2 / 1_000_000
        
        return {
            'total_area_km2': round(total_area_km2, 2),
            'affected_area_km2': round(affected_area_km2, 2),
            'affected_area_m2': round(affected_area_m2, 0),
            'percentage': round(percentage, 2),
            'total_pixels': total_pixels,
            'affected_pixels': affected_pixels
        }
    
    def _calculate_bbox(
        self,
        lat: float,
        lon: float,
        zoom: int,
        width: int,
        height: int
    ) -> Tuple[float, float, float, float]:
        """
        Calcule bounding box à partir de centre et zoom
        
        Args:
            lat, lon: Centre
            zoom: Niveau zoom
            width, height: Dimensions image en pixels
        
        Returns:
            (min_lon, min_lat, max_lon, max_lat)
        """
        
        # Résolution approximative par niveau de zoom (mètres/pixel à l'équateur)
        # zoom 0: 156543 m/px
        # zoom 10: 153 m/px
        # zoom 15: 4.8 m/px
        
        resolution_m_per_px = 156543 / (2 ** zoom)
        
        # Ajuster pour latitude
        resolution_m_per_px /= np.cos(np.radians(lat))
        
        # Taille en mètres
        width_m = width * resolution_m_per_px
        height_m = height * resolution_m_per_px
        
        # Convertir en degrés (approximation)
        lat_offset = (height_m / 2) / 111320  # 1 degré lat ≈ 111.32 km
        lon_offset = (width_m / 2) / (111320 * np.cos(np.radians(lat)))
        
        return (
            lon - lon_offset,  # min_lon
            lat - lat_offset,  # min_lat
            lon + lon_offset,  # max_lon
            lat + lat_offset   # max_lat
        )
    
    def get_usage_stats(self) -> Dict:
        """Retourne statistiques d'usage des APIs"""
        return st.session_state.get('satellite_stats', {})
    
    def encode_image_base64(self, image: np.ndarray) -> str:
        """
        Encode une image en base64 pour affichage HTML
        
        Args:
            image: Image numpy array
        
        Returns:
            String base64
        """
        
        img_pil = Image.fromarray(image)
        buffered = BytesIO()
        img_pil.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"