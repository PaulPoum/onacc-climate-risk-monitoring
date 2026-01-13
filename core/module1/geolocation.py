# core/module1/geolocation.py
"""
Service de géolocalisation et reverse geocoding
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, Optional
import requests
from datetime import datetime

class GeolocationService:
    """Service de géolocalisation utilisateur et reverse geocoding"""
    
    def __init__(self):
        self.default_location = {
            'lat': 3.8480,
            'lon': 11.5021,
            'localite': 'Yaoundé',
            'region': 'Centre',
            'accuracy': 0,
            'method': 'default',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_user_location(self) -> Dict:
        """
        Obtient la géolocalisation de l'utilisateur via HTML5 Geolocation API
        
        Returns:
            Dict avec lat, lon, localite, region, accuracy, method
        """
        
        # Vérifier si déjà en session (évite multiples requêtes)
        if 'user_geolocation' in st.session_state:
            cached_location = st.session_state['user_geolocation']
            
            # Vérifier si cache pas trop ancien (5 minutes)
            cache_time = datetime.fromisoformat(cached_location.get('timestamp', '2000-01-01'))
            if (datetime.now() - cache_time).seconds < 300:
                return cached_location
        
        # Composant HTML/JS pour géolocalisation
        geolocation_component = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body>
        <script>
        function sendLocationToStreamlit(data) {
            // Méthode compatible Streamlit
            const event = new CustomEvent('streamlit:setComponentValue', {
                detail: data
            });
            window.parent.document.dispatchEvent(event);
            
            // Alternative: postMessage
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: data
            }, '*');
        }
        
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    position => {
                        const data = {
                            lat: position.coords.latitude,
                            lon: position.coords.longitude,
                            accuracy: position.coords.accuracy,
                            method: 'html5',
                            timestamp: new Date().toISOString()
                        };
                        sendLocationToStreamlit(data);
                    },
                    error => {
                        console.error('Erreur géolocalisation:', error.message);
                        // Fallback position par défaut (Yaoundé)
                        const data = {
                            lat: 3.8480,
                            lon: 11.5021,
                            accuracy: 0,
                            method: 'default',
                            error: error.message,
                            timestamp: new Date().toISOString()
                        };
                        sendLocationToStreamlit(data);
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 300000  // Cache 5 minutes
                    }
                );
            } else {
                // Navigateur ne supporte pas géolocalisation
                const data = {
                    lat: 3.8480,
                    lon: 11.5021,
                    accuracy: 0,
                    method: 'default',
                    error: 'Geolocation not supported',
                    timestamp: new Date().toISOString()
                };
                sendLocationToStreamlit(data);
            }
        }
        
        // Exécuter immédiatement
        getLocation();
        </script>
        </body>
        </html>
        """
        
        # Afficher le composant (invisible)
        location_data = components.html(geolocation_component, height=0)
        
        if location_data and isinstance(location_data, dict) and 'lat' in location_data:
            # Enrichir avec reverse geocoding
            location = self.reverse_geocode(
                location_data['lat'],
                location_data['lon']
            )
            location['accuracy'] = location_data.get('accuracy', 0)
            location['method'] = location_data.get('method', 'html5')
            location['timestamp'] = location_data.get('timestamp', datetime.now().isoformat())
            
            # Mettre en cache
            st.session_state['user_geolocation'] = location
            
            return location
        
        # Fallback : retourner position par défaut
        st.session_state['user_geolocation'] = self.default_location
        return self.default_location
    
    @st.cache_data(ttl=3600)  # Cache 1 heure
    def reverse_geocode(_self, lat: float, lon: float) -> Dict:
        """
        Reverse geocoding avec Nominatim (OpenStreetMap)
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            Dict avec lat, lon, localite, region
        """
        
        try:
            # API Nominatim (gratuite, respecter Usage Policy)
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 10,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'ONACC-Platform/1.0 (contact@onacc.cm)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                address = data.get('address', {})
                
                return {
                    'lat': lat,
                    'lon': lon,
                    'localite': (
                        address.get('city') or 
                        address.get('town') or 
                        address.get('village') or 
                        address.get('suburb') or
                        'Position actuelle'
                    ),
                    'region': (
                        address.get('state') or 
                        address.get('region') or 
                        'Non déterminé'
                    ),
                    'pays': address.get('country', 'Cameroun'),
                    'geocoding': 'nominatim'
                }
        
        except Exception as e:
            st.warning(f"⚠️ Reverse geocoding échoué: {e}")
        
        # Fallback : essayer de trouver via stations proches
        return _self.find_nearest_station_location(lat, lon)
    
    def find_nearest_station_location(self, lat: float, lon: float) -> Dict:
        """
        Trouve la station la plus proche pour déterminer la localité
        
        Args:
            lat: Latitude utilisateur
            lon: Longitude utilisateur
        
        Returns:
            Dict avec informations de la station la plus proche
        """
        
        try:
            from core.supabase_client import supabase_user
            from core.module1.utils import haversine_distance
            
            u = supabase_user(st.session_state["access_token"])
            
            # Récupérer toutes les stations
            stations = u.table("mnocc_stations").select("*").execute().data
            
            if stations:
                # Trouver la plus proche
                nearest = min(
                    stations,
                    key=lambda s: haversine_distance(
                        lat, lon,
                        s['latitude'], s['longitude']
                    )
                )
                
                distance = haversine_distance(
                    lat, lon,
                    nearest['latitude'], nearest['longitude']
                )
                
                return {
                    'lat': lat,
                    'lon': lon,
                    'localite': f"Près de {nearest['localite']}",
                    'region': nearest['region'],
                    'nearest_station': nearest['localite'],
                    'distance_km': round(distance, 1),
                    'geocoding': 'nearest_station'
                }
        
        except Exception as e:
            st.warning(f"⚠️ Recherche station proche échouée: {e}")
        
        # Ultimate fallback
        return {
            'lat': lat,
            'lon': lon,
            'localite': 'Position actuelle',
            'region': 'Non déterminé',
            'geocoding': 'fallback'
        }
    
    def get_administrative_zone(self, lat: float, lon: float) -> Dict:
        """
        Détermine la zone administrative (région, département, arrondissement)
        
        TODO: À implémenter après création table administrative_zones avec PostGIS
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            Dict avec région, département, arrondissement
        """
        
        # Placeholder pour future implémentation
        # Nécessite table PostGIS avec géométries administratives
        
        return {
            'region': 'À déterminer',
            'departement': 'À déterminer',
            'arrondissement': 'À déterminer',
            'note': 'Nécessite implémentation PostGIS'
        }