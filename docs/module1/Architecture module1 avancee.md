# 🚀 ARCHITECTURE AVANCÉE MODULE 1 - SOLUTION INNOVANTE

## 🎯 Vue d'Ensemble

**Plateforme intelligente de veille hydrométéorologique** avec IA, imagerie satellite, modèles hydrologiques et géolocalisation en temps réel.

---

## 📐 ARCHITECTURE GLOBALE

### **Stack Technologique Complet**

```
┌────────────────────────────────────────────────────────────┐
│                    INTERFACE UTILISATEUR                    │
│              Streamlit + React Components                   │
└────────────────────┬───────────────────────────────────────┘
                     │
┌────────────────────┴───────────────────────────────────────┐
│                   COUCHE PRÉSENTATION                       │
│  • Géolocalisation HTML5 (Navigator API)                   │
│  • Leaflet.js pour cartes interactives                     │
│  • Plotly pour graphiques avancés                          │
│  • PDF Generation (WeasyPrint / ReportLab)                 │
└────────────────────┬───────────────────────────────────────┘
                     │
┌────────────────────┴───────────────────────────────────────┐
│                  COUCHE MÉTIER (Backend)                    │
│  ┌──────────────┬──────────────┬──────────────┬─────────┐ │
│  │   ML Engine  │ Hydro Models │  Satellite   │ Alertes │ │
│  │  (Prédictif) │  (Physique)  │  (Imagerie)  │ (Notif) │ │
│  └──────────────┴──────────────┴──────────────┴─────────┘ │
└────────────────────┬───────────────────────────────────────┘
                     │
┌────────────────────┴───────────────────────────────────────┐
│                     COUCHE DONNÉES                          │
│  • Supabase (PostgreSQL + PostGIS)                         │
│  • Redis (Cache temps réel)                                │
│  • MinIO / S3 (Images satellite)                           │
│  • InfluxDB (Séries temporelles)                           │
└────────────────────┬───────────────────────────────────────┘
                     │
┌────────────────────┴───────────────────────────────────────┐
│                 SOURCES DE DONNÉES EXTERNES                 │
│  • Open-Meteo API (Prévisions)                             │
│  • Sentinel Hub / Copernicus (Satellite)                   │
│  • SRTM DEM (Modèle Numérique de Terrain)                  │
│  • ONACC Stations (Observations terrain)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌍 1. GÉOLOCALISATION AUTOMATIQUE

### **Solution : Géolocalisation HTML5 + Reverse Geocoding**

#### **A. Composant JavaScript Géolocalisation**

```javascript
// components/geolocation.js
function getUserLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Géolocalisation non supportée'));
        }
        
        navigator.geolocation.getCurrentPosition(
            position => {
                resolve({
                    lat: position.coords.latitude,
                    lon: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: new Date().toISOString()
                });
            },
            error => {
                reject(error);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000 // Cache 5 minutes
            }
        );
    });
}

// Reverse geocoding avec Nominatim
async function reverseGeocode(lat, lon) {
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=10`;
    const response = await fetch(url);
    const data = await response.json();
    
    return {
        region: data.address.state,
        departement: data.address.county,
        arrondissement: data.address.municipality || data.address.town,
        localite: data.address.city || data.address.village
    };
}

// Envoyer à Streamlit
async function sendLocationToStreamlit() {
    try {
        const location = await getUserLocation();
        const address = await reverseGeocode(location.lat, location.lon);
        
        // Streamlit set_component_value
        Streamlit.setComponentValue({
            ...location,
            ...address
        });
    } catch (error) {
        console.error('Erreur géolocalisation:', error);
    }
}
```

#### **B. Intégration Streamlit**

```python
import streamlit.components.v1 as components

def get_user_geolocation():
    """Obtient la géolocalisation de l'utilisateur"""
    
    # Composant HTML/JS
    geolocation_html = """
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                position => {
                    const data = {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    };
                    
                    // Envoyer à Streamlit
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        data: data
                    }, '*');
                },
                error => {
                    console.error('Erreur géolocalisation:', error);
                    // Position par défaut (Yaoundé)
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        data: {lat: 3.8480, lon: 11.5021, accuracy: 0}
                    }, '*');
                }
            );
        }
    }
    getLocation();
    </script>
    """
    
    location = components.html(geolocation_html, height=0)
    
    if location:
        return location
    else:
        # Par défaut : Yaoundé
        return {'lat': 3.8480, 'lon': 11.5021, 'accuracy': 0}
```

#### **C. Reverse Geocoding avec PostGIS**

```python
def get_administrative_divisions(lat: float, lon: float) -> Dict:
    """Détermine région, département, arrondissement à partir de coordonnées"""
    
    query = """
    WITH point AS (
        SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS geom
    )
    SELECT 
        r.nom AS region,
        d.nom AS departement,
        a.nom AS arrondissement,
        ST_Distance(
            point.geom::geography,
            s.location::geography
        ) AS distance
    FROM point
    CROSS JOIN LATERAL (
        SELECT 
            nom,
            location,
            region_id,
            departement_id
        FROM mnocc_stations
        ORDER BY location <-> point.geom
        LIMIT 1
    ) s
    LEFT JOIN regions r ON r.id = s.region_id
    LEFT JOIN departements d ON d.id = s.departement_id
    LEFT JOIN arrondissements a ON a.id = s.arrondissement_id
    """
    
    result = supabase_client.rpc('execute_sql', {'query': query, 'params': [lon, lat]}).execute()
    return result.data[0] if result.data else None
```

---

## 🛰️ 2. IMAGERIE SATELLITE

### **Solution : Sentinel Hub + Google Earth Engine**

#### **A. Sources d'Imagerie**

**1. Sentinel-2 (Optique - 10m résolution)**
- Bandes multispectales
- Passage tous les 5 jours
- Gratuit via Copernicus

**2. Sentinel-1 (Radar SAR)**
- Pénètre nuages
- Détection inondations
- Indépendant de la météo

**3. MODIS (Basse résolution - 250m)**
- Temps réel
- Couverture quotidienne
- Indices de végétation

#### **B. API Sentinel Hub**

```python
from sentinelhub import (
    SHConfig,
    BBox,
    CRS,
    MimeType,
    SentinelHubRequest,
    DataCollection
)

class SatelliteImageryService:
    """Service d'imagerie satellite"""
    
    def __init__(self):
        self.config = SHConfig()
        self.config.sh_client_id = st.secrets["SENTINEL_CLIENT_ID"]
        self.config.sh_client_secret = st.secrets["SENTINEL_CLIENT_SECRET"]
    
    def get_flood_detection_image(
        self,
        bbox: Tuple[float, float, float, float],
        date_from: str,
        date_to: str
    ) -> np.ndarray:
        """
        Détecte les zones inondées via Sentinel-1 SAR
        
        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat)
            date_from: 'YYYY-MM-DD'
            date_to: 'YYYY-MM-DD'
        
        Returns:
            Image numpy array avec masque inondation
        """
        
        # Script de détection inondation (VV polarization)
        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: [{bands: ["VV", "VH"]}],
                output: {bands: 3}
            };
        }

        function evaluatePixel(sample) {
            // Détection eau : VV < -15 dB
            let water = sample.VV < 0.03;
            
            return [
                water ? 0 : sample.VV * 2,  // R
                water ? 0 : sample.VV * 2,  // G
                water ? 1 : sample.VV * 2   // B (bleu pour eau)
            ];
        }
        """
        
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL1_IW,
                    time_interval=(date_from, date_to)
                )
            ],
            responses=[
                SentinelHubRequest.output_response('default', MimeType.PNG)
            ],
            bbox=BBox(bbox=bbox, crs=CRS.WGS84),
            size=(512, 512),
            config=self.config
        )
        
        return request.get_data()[0]
    
    def get_ndvi_image(
        self,
        bbox: Tuple[float, float, float, float],
        date: str
    ) -> np.ndarray:
        """
        Calcule NDVI (Normalized Difference Vegetation Index)
        Indicateur de sécheresse
        """
        
        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: [{bands: ["B04", "B08"]}],
                output: {bands: 1, sampleType: "FLOAT32"}
            };
        }

        function evaluatePixel(sample) {
            let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
            return [ndvi];
        }
        """
        
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=(date, date)
                )
            ],
            responses=[
                SentinelHubRequest.output_response('default', MimeType.TIFF)
            ],
            bbox=BBox(bbox=bbox, crs=CRS.WGS84),
            size=(512, 512),
            config=self.config
        )
        
        return request.get_data()[0]
    
    def calculate_affected_area(
        self,
        flood_mask: np.ndarray,
        pixel_size_m: float = 10.0
    ) -> float:
        """Calcule la surface affectée en km²"""
        
        n_flooded_pixels = np.sum(flood_mask > 0)
        area_m2 = n_flooded_pixels * (pixel_size_m ** 2)
        area_km2 = area_m2 / 1_000_000
        
        return area_km2
```

#### **C. Visualisation avec Folium**

```python
import folium
from folium import plugins

def create_satellite_overlay_map(
    center: Tuple[float, float],
    satellite_image: np.ndarray,
    bbox: Tuple[float, float, float, float],
    affected_area_km2: float
) -> folium.Map:
    """Crée une carte avec overlay satellite"""
    
    m = folium.Map(
        location=center,
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Overlay image satellite
    folium.raster_layers.ImageOverlay(
        image=satellite_image,
        bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
        opacity=0.6,
        name='Détection Inondation',
        interactive=True
    ).add_to(m)
    
    # Légende
    legend_html = f"""
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; border-radius:5px; padding:10px">
    <p><strong>Détection Inondation</strong></p>
    <p style="color:blue;">🟦 Zone inondée</p>
    <p><strong>Surface:</strong> {affected_area_km2:.2f} km²</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Layer control
    folium.LayerControl().add_to(m)
    
    return m
```

---

## 🌊 3. MODÈLES HYDROLOGIQUES

### **Solution : HEC-RAS + GR4J + Machine Learning**

#### **A. Modèle GR4J (Modèle Pluie-Débit)**

```python
import numpy as np
from scipy.optimize import minimize

class GR4JModel:
    """
    Modèle hydrologique GR4J (Génie Rural à 4 paramètres Journalier)
    Développé par INRAE (France)
    """
    
    def __init__(self):
        self.params = None  # [X1, X2, X3, X4]
    
    def production_store(self, P: float, E: float, S: float, X1: float) -> Tuple[float, float, float]:
        """
        Réservoir de production
        
        Args:
            P: Précipitation (mm)
            E: Évapotranspiration (mm)
            S: État du réservoir de production (mm)
            X1: Capacité max du réservoir (mm)
        
        Returns:
            (Pn, En, S_new)
        """
        
        if P >= E:
            # Pluie nette
            En = 0
            Ws = (P - E) / X1
            
            if Ws > 13:
                Ps = (P - E)
            else:
                tanh_ws = np.tanh(Ws)
                Ps = X1 * (1 - (S / X1) ** 2) * tanh_ws / (1 + (S / X1) * tanh_ws)
            
            S_new = min(S + Ps, X1)
            Pn = P - E - Ps
        else:
            # Évaporation nette
            Pn = 0
            Ws = (E - P) / X1
            
            if Ws > 13:
                Es = S
            else:
                tanh_ws = np.tanh(Ws)
                Es = S * (2 - S / X1) * tanh_ws / (1 + (1 - S / X1) * tanh_ws)
            
            S_new = max(S - Es, 0)
            En = E - P - Es
        
        return Pn, En, S_new
    
    def routing_store(self, Perc: float, R: float, X3: float) -> Tuple[float, float]:
        """Réservoir de routage"""
        
        R_new = max(0, R + Perc)
        
        if R_new > 0:
            Qr = R_new * (1 - (1 + (R_new / X3) ** 4) ** (-0.25))
        else:
            Qr = 0
        
        R_new = R_new - Qr
        
        return Qr, R_new
    
    def unit_hydrograph(self, X4: float, n_steps: int = 20) -> np.ndarray:
        """Hydrogramme unitaire (HU1 et HU2)"""
        
        UH1 = np.zeros(n_steps)
        UH2 = np.zeros(n_steps * 2)
        
        for t in range(n_steps):
            if t < X4:
                UH1[t] = (t / X4) ** 2.5
            else:
                UH1[t] = 1.0
        
        for t in range(n_steps * 2):
            if t < X4:
                UH2[t] = 0.5 * (t / X4) ** 2.5
            elif t < 2 * X4:
                UH2[t] = 1 - 0.5 * (2 - t / X4) ** 2.5
            else:
                UH2[t] = 1.0
        
        # Différences pour obtenir les poids
        UH1 = np.diff(np.concatenate([[0], UH1]))
        UH2 = np.diff(np.concatenate([[0], UH2]))
        
        return UH1, UH2
    
    def simulate(
        self,
        P: np.ndarray,
        E: np.ndarray,
        params: List[float]
    ) -> np.ndarray:
        """
        Simule le débit
        
        Args:
            P: Précipitations (mm/jour)
            E: Évapotranspiration (mm/jour)
            params: [X1, X2, X3, X4]
        
        Returns:
            Q: Débit simulé (mm/jour)
        """
        
        X1, X2, X3, X4 = params
        n = len(P)
        
        # Initialisation
        S = X1 * 0.5  # Réservoir production à 50%
        R = X3 * 0.5  # Réservoir routage à 50%
        
        UH1, UH2 = self.unit_hydrograph(X4)
        
        Q = np.zeros(n)
        UH1_queue = np.zeros(len(UH1))
        UH2_queue = np.zeros(len(UH2))
        
        for t in range(n):
            # Production store
            Pn, En, S = self.production_store(P[t], E[t], S, X1)
            
            # Percolation
            Perc = S * (1 - (1 + (S / 2.25 / X1) ** 4) ** (-0.25))
            S = S - Perc
            
            # Répartition
            Pr = Perc + Pn * 0.9  # 90% au routage
            
            # Unit hydrographs
            UH1_queue = np.roll(UH1_queue, 1)
            UH1_queue[0] = Pr
            Q1 = np.sum(UH1_queue * UH1)
            
            UH2_queue = np.roll(UH2_queue, 1)
            UH2_queue[0] = Pr
            Q9 = np.sum(UH2_queue * UH2)
            
            # Routing store
            Qr, R = self.routing_store(Q9, R, X3)
            
            # Exchange
            F = X2 * (R / X3) ** 3.5
            
            # Débit total
            Qd = max(0, Q1 + F)
            Q[t] = Qd
        
        return Q
    
    def calibrate(
        self,
        P: np.ndarray,
        E: np.ndarray,
        Q_obs: np.ndarray
    ) -> List[float]:
        """Calibre le modèle sur données observées"""
        
        def objective(params):
            Q_sim = self.simulate(P, E, params)
            # Nash-Sutcliffe Efficiency
            nse = 1 - np.sum((Q_obs - Q_sim) ** 2) / np.sum((Q_obs - np.mean(Q_obs)) ** 2)
            return -nse  # Minimize negative NSE
        
        # Bornes des paramètres
        bounds = [
            (100, 1200),   # X1: Capacité production (mm)
            (-5, 3),       # X2: Échange souterrain (mm)
            (20, 300),     # X3: Capacité routage (mm)
            (1, 5)         # X4: Temps de base HU (jours)
        ]
        
        # Optimisation
        result = minimize(
            objective,
            x0=[350, 0, 90, 1.7],  # Valeurs initiales
            bounds=bounds,
            method='L-BFGS-B'
        )
        
        self.params = result.x
        return self.params
```

#### **B. Intégration Prévisions**

```python
class FloodForecastSystem:
    """Système de prévision des crues"""
    
    def __init__(self):
        self.gr4j = GR4JModel()
        self.calibrated_basins = {}
    
    def forecast_discharge(
        self,
        basin_id: str,
        forecast_precipitation: np.ndarray,
        forecast_et: np.ndarray
    ) -> Dict:
        """
        Prévoit le débit pour un bassin versant
        
        Returns:
            {
                'discharge': np.ndarray,  # m³/s
                'flood_risk': 'low'|'moderate'|'high'|'critical',
                'peak_time': datetime,
                'peak_value': float
            }
        """
        
        # Charger paramètres calibrés
        params = self.calibrated_basins.get(basin_id)
        
        if params is None:
            # Paramètres par défaut si non calibré
            params = [350, 0, 90, 1.7]
        
        # Simuler débit
        Q = self.gr4j.simulate(forecast_precipitation, forecast_et, params)
        
        # Analyser risque
        Q_mean = np.mean(Q)
        Q_max = np.max(Q)
        
        # Seuils de crue (à adapter par bassin)
        thresholds = {
            'low': Q_mean * 2,
            'moderate': Q_mean * 5,
            'high': Q_mean * 10,
            'critical': Q_mean * 20
        }
        
        if Q_max >= thresholds['critical']:
            risk = 'critical'
        elif Q_max >= thresholds['high']:
            risk = 'high'
        elif Q_max >= thresholds['moderate']:
            risk = 'moderate'
        else:
            risk = 'low'
        
        # Temps du pic
        peak_idx = np.argmax(Q)
        peak_time = datetime.now() + timedelta(days=int(peak_idx))
        
        return {
            'discharge': Q,
            'flood_risk': risk,
            'peak_time': peak_time,
            'peak_value': Q_max,
            'mean_discharge': Q_mean
        }
```

---

## 🧠 4. MACHINE LEARNING PRÉDICTIF

### **Solution : LSTM + Random Forest + XGBoost**

#### **A. Modèle LSTM pour Séries Temporelles**

```python
import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import MinMaxScaler

class LSTMFloodPredictor:
    """Prédicteur de crues basé sur LSTM"""
    
    def __init__(self):
        self.model = None
        self.scaler_X = MinMaxScaler()
        self.scaler_y = MinMaxScaler()
        self.lookback = 30  # 30 jours d'historique
    
    def build_model(self, n_features: int):
        """Construit l'architecture LSTM"""
        
        model = keras.Sequential([
            # LSTM layers
            keras.layers.LSTM(
                128, 
                return_sequences=True,
                input_shape=(self.lookback, n_features)
            ),
            keras.layers.Dropout(0.2),
            
            keras.layers.LSTM(64, return_sequences=True),
            keras.layers.Dropout(0.2),
            
            keras.layers.LSTM(32),
            keras.layers.Dropout(0.2),
            
            # Dense layers
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dense(1)  # Prédiction débit
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        self.model = model
        return model
    
    def prepare_sequences(
        self,
        data: np.ndarray,
        target: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prépare les séquences pour LSTM"""
        
        X, y = [], []
        
        for i in range(self.lookback, len(data)):
            X.append(data[i - self.lookback:i])
            y.append(target[i])
        
        return np.array(X), np.array(y)
    
    def train(
        self,
        precipitation: np.ndarray,
        temperature: np.ndarray,
        humidity: np.ndarray,
        discharge: np.ndarray,
        epochs: int = 100
    ):
        """Entraîne le modèle"""
        
        # Préparer features
        X_data = np.column_stack([precipitation, temperature, humidity])
        
        # Normaliser
        X_scaled = self.scaler_X.fit_transform(X_data)
        y_scaled = self.scaler_y.fit_transform(discharge.reshape(-1, 1))
        
        # Créer séquences
        X, y = self.prepare_sequences(X_scaled, y_scaled)
        
        # Split train/val
        split = int(0.8 * len(X))
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]
        
        # Build model
        if self.model is None:
            self.build_model(n_features=X.shape[2])
        
        # Callbacks
        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        reduce_lr = keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5
        )
        
        # Train
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=32,
            callbacks=[early_stop, reduce_lr],
            verbose=1
        )
        
        return history
    
    def predict(
        self,
        recent_data: np.ndarray,
        horizon: int = 10
    ) -> np.ndarray:
        """
        Prédit le débit futur
        
        Args:
            recent_data: Dernières observations (lookback x n_features)
            horizon: Nombre de jours à prédire
        
        Returns:
            Prédictions de débit (horizon,)
        """
        
        predictions = []
        current_sequence = recent_data[-self.lookback:]
        
        for _ in range(horizon):
            # Normaliser
            current_scaled = self.scaler_X.transform(current_sequence)
            
            # Prédire
            pred_scaled = self.model.predict(
                current_scaled.reshape(1, self.lookback, -1),
                verbose=0
            )
            
            # Dénormaliser
            pred = self.scaler_y.inverse_transform(pred_scaled)[0, 0]
            predictions.append(pred)
            
            # Update sequence (rolling window)
            # Note: Ici on devrait aussi prédire les features futures
            # Pour simplifier, on garde la dernière valeur
            current_sequence = np.roll(current_sequence, -1, axis=0)
            current_sequence[-1] = current_sequence[-2]  # Copie dernière valeur
        
        return np.array(predictions)
```

#### **B. Random Forest pour Classification Risque**

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

class RiskClassifier:
    """Classifie le niveau de risque"""
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=10,
            class_weight='balanced',
            random_state=42
        )
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crée des features avancées"""
        
        features = pd.DataFrame()
        
        # Features de base
        features['precip_sum_7d'] = df['precipitation'].rolling(7).sum()
        features['precip_sum_14d'] = df['precipitation'].rolling(14).sum()
        features['precip_max_3d'] = df['precipitation'].rolling(3).max()
        
        # Jours secs consécutifs
        features['dry_days'] = (df['precipitation'] < 1).astype(int)
        features['max_dry_streak'] = features['dry_days'].rolling(30).apply(
            lambda x: max(len(list(g)) for k, g in groupby(x) if k == 1),
            raw=False
        )
        
        # Température
        features['temp_mean_7d'] = df['temperature'].rolling(7).mean()
        features['temp_max_7d'] = df['temperature'].rolling(7).max()
        features['heat_days'] = (df['temperature'] > 35).astype(int).rolling(7).sum()
        
        # Évapotranspiration approximative
        features['et_penman'] = 0.408 * (
            0.0023 * (df['temperature'] + 17.8) *
            np.sqrt(df['temperature_max'] - df['temperature_min'])
        )
        
        # Déficit hydrique
        features['water_deficit'] = (features['precip_sum_14d'] - 
                                     features['et_penman'].rolling(14).sum())
        
        # Saisonnalité
        features['month'] = df.index.month
        features['season'] = features['month'].apply(
            lambda x: 'wet' if 5 <= x <= 10 else 'dry'
        )
        
        # One-hot encode season
        features = pd.get_dummies(features, columns=['season'])
        
        return features
    
    def train(self, X: pd.DataFrame, y: pd.Series):
        """Entraîne le classificateur"""
        
        # Cross-validation
        scores = cross_val_score(self.model, X, y, cv=5, scoring='f1_weighted')
        print(f"CV F1-Score: {scores.mean():.3f} (+/- {scores.std():.3f})")
        
        # Train on all data
        self.model.fit(X, y)
        
        # Feature importance
        importances = pd.DataFrame({
            'feature': X.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return importances
    
    def predict_risk(self, X: pd.DataFrame) -> Dict:
        """Prédit le risque avec probabilités"""
        
        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)
        
        return {
            'risk_level': predictions[0],
            'probabilities': {
                cls: prob
                for cls, prob in zip(self.model.classes_, probabilities[0])
            }
        }
```

---

## 🔔 5. SYSTÈME DE NOTIFICATIONS

### **Solution : Multi-Canal (Email, SMS, Push, WhatsApp)**

```python
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AlertNotificationSystem:
    """Système de notifications multi-canal"""
    
    def __init__(self):
        # Twilio pour SMS
        self.twilio_client = Client(
            st.secrets["TWILIO_ACCOUNT_SID"],
            st.secrets["TWILIO_AUTH_TOKEN"]
        )
        
        # SMTP pour Email
        self.smtp_server = st.secrets["SMTP_SERVER"]
        self.smtp_port = st.secrets["SMTP_PORT"]
        self.smtp_user = st.secrets["SMTP_USER"]
        self.smtp_password = st.secrets["SMTP_PASSWORD"]
    
    def send_sms(self, to: str, message: str):
        """Envoie SMS via Twilio"""
        
        try:
            message = self.twilio_client.messages.create(
                body=message,
                from_=st.secrets["TWILIO_PHONE_NUMBER"],
                to=to
            )
            return message.sid
        except Exception as e:
            print(f"Erreur SMS: {e}")
            return None
    
    def send_email(self, to: str, subject: str, html_content: str):
        """Envoie Email via SMTP"""
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.smtp_user
        msg['To'] = to
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Erreur Email: {e}")
            return False
    
    def send_alert(
        self,
        alert_type: str,
        risk_level: str,
        region: str,
        details: Dict,
        recipients: List[Dict]
    ):
        """
        Envoie une alerte multi-canal
        
        Args:
            alert_type: 'flood' | 'drought' | 'heatwave'
            risk_level: 'low' | 'moderate' | 'high' | 'critical'
            region: Nom de la région
            details: Détails de l'alerte
            recipients: Liste [{name, email, phone, channels}]
        """
        
        # Formater le message
        if alert_type == 'flood':
            emoji = '🌊'
            type_fr = 'INONDATION'
        elif alert_type == 'drought':
            emoji = '🌵'
            type_fr = 'SÉCHERESSE'
        else:
            emoji = '🔥'
            type_fr = 'CHALEUR'
        
        # Message SMS (court)
        sms_text = f"""
{emoji} ALERTE {risk_level.upper()} - {type_fr}

Région: {region}
{details.get('summary', '')}

ONACC Climate Risk
        """.strip()
        
        # Email HTML (détaillé)
        email_html = f"""
        <html>
        <head>
            <style>
                .alert-box {{
                    background: {'#f8d7da' if risk_level == 'critical' else '#fff3cd'};
                    border-left: 5px solid {'#f44336' if risk_level == 'critical' else '#ff9800'};
                    padding: 20px;
                    margin: 20px 0;
                }}
                .metric {{
                    display: inline-block;
                    margin: 10px 20px;
                }}
            </style>
        </head>
        <body>
            <h1>{emoji} ALERTE {risk_level.upper()} - {type_fr}</h1>
            
            <div class="alert-box">
                <h2>Région: {region}</h2>
                <p><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><strong>Validité:</strong> {details.get('validity', '48h')}</p>
            </div>
            
            <h3>Détails:</h3>
            <p>{details.get('description', '')}</p>
            
            <h3>Métriques:</h3>
            {self._format_metrics_html(details.get('metrics', {}))}
            
            <h3>Recommandations:</h3>
            <ul>
                {''.join(f'<li>{rec}</li>' for rec in details.get('recommendations', []))}
            </ul>
            
            <hr>
            <p style="color: #666;">
                ONACC Climate Risk Monitoring Platform<br>
                <a href="https://onacc.cm">onacc.cm</a>
            </p>
        </body>
        </html>
        """
        
        # Envoi multi-canal
        for recipient in recipients:
            channels = recipient.get('channels', ['email'])
            
            if 'sms' in channels and recipient.get('phone'):
                self.send_sms(recipient['phone'], sms_text)
            
            if 'email' in channels and recipient.get('email'):
                self.send_email(
                    recipient['email'],
                    f"[ALERTE {risk_level.upper()}] {type_fr} - {region}",
                    email_html
                )
    
    def _format_metrics_html(self, metrics: Dict) -> str:
        """Formate les métriques en HTML"""
        html = '<div>'
        for key, value in metrics.items():
            html += f'<div class="metric"><strong>{key}:</strong> {value}</div>'
        html += '</div>'
        return html
```

---

## 📄 6. GÉNÉRATION RAPPORTS PDF

### **Solution : WeasyPrint + Jinja2 Templates**

```python
from weasyprint import HTML, CSS
from jinja2 import Template
import base64
from io import BytesIO

class PDFReportGenerator:
    """Générateur de rapports PDF professionnels"""
    
    def __init__(self):
        self.template = self._load_template()
    
    def _load_template(self) -> Template:
        """Charge le template Jinja2"""
        
        template_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {
                    size: A4;
                    margin: 2cm;
                    @bottom-right {
                        content: "Page " counter(page) " / " counter(pages);
                    }
                }
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    color: #333;
                }
                .header {
                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    margin-bottom: 30px;
                }
                .section {
                    margin-bottom: 30px;
                    page-break-inside: avoid;
                }
                .kpi-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin-bottom: 30px;
                }
                .kpi-box {
                    border: 2px solid #e0e0e0;
                    padding: 15px;
                    text-align: center;
                    border-radius: 8px;
                }
                .kpi-value {
                    font-size: 2em;
                    font-weight: bold;
                    color: #4facfe;
                }
                .risk-critical { color: #f44336; }
                .risk-high { color: #ff9800; }
                .risk-moderate { color: #ffc107; }
                .risk-low { color: #4caf50; }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 15px;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }
                th {
                    background-color: #4facfe;
                    color: white;
                }
                .chart {
                    width: 100%;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ title }}</h1>
                <p>{{ subtitle }}</p>
                <p>Généré le {{ generation_date }}</p>
            </div>
            
            <!-- KPIs -->
            <div class="section">
                <h2>📊 Indicateurs Clés</h2>
                <div class="kpi-grid">
                    {% for kpi in kpis %}
                    <div class="kpi-box">
                        <div class="kpi-value">{{ kpi.value }}</div>
                        <div>{{ kpi.label }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Risques -->
            <div class="section">
                <h2>⚠️ Évaluation des Risques</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Région</th>
                            <th>Risque Inondation</th>
                            <th>Risque Sécheresse</th>
                            <th>Actions Recommandées</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for risk in risks %}
                        <tr>
                            <td>{{ risk.region }}</td>
                            <td class="risk-{{ risk.flood_level }}">{{ risk.flood_label }}</td>
                            <td class="risk-{{ risk.drought_level }}">{{ risk.drought_label }}</td>
                            <td>{{ risk.actions }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <!-- Graphiques -->
            <div class="section">
                <h2>📈 Visualisations</h2>
                {% for chart in charts %}
                <div>
                    <h3>{{ chart.title }}</h3>
                    <img src="data:image/png;base64,{{ chart.image_base64 }}" class="chart">
                </div>
                {% endfor %}
            </div>
            
            <!-- Recommandations -->
            <div class="section">
                <h2>💡 Recommandations</h2>
                <ul>
                    {% for rec in recommendations %}
                    <li>{{ rec }}</li>
                    {% endfor %}
                </ul>
            </div>
            
            <div class="footer" style="text-align: center; margin-top: 50px; color: #666;">
                <hr>
                <p>ONACC - Observatoire National sur les Changements Climatiques</p>
                <p>www.onacc.cm</p>
            </div>
        </body>
        </html>
        """
        
        return Template(template_html)
    
    def generate_report(
        self,
        title: str,
        subtitle: str,
        kpis: List[Dict],
        risks: List[Dict],
        charts: List[go.Figure],
        recommendations: List[str]
    ) -> bytes:
        """
        Génère un rapport PDF
        
        Returns:
            Bytes du PDF
        """
        
        # Convertir graphiques Plotly en images base64
        chart_data = []
        for chart in charts:
            img_bytes = chart.to_image(format="png", width=800, height=400)
            img_base64 = base64.b64encode(img_bytes).decode()
            chart_data.append({
                'title': chart.layout.title.text,
                'image_base64': img_base64
            })
        
        # Rendre le template
        html_content = self.template.render(
            title=title,
            subtitle=subtitle,
            generation_date=datetime.now().strftime('%d/%m/%Y %H:%M'),
            kpis=kpis,
            risks=risks,
            charts=chart_data,
            recommendations=recommendations
        )
        
        # Générer PDF
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        return pdf_bytes
    
    def generate_and_download(
        self,
        filename: str,
        **kwargs
    ):
        """Génère et propose le téléchargement dans Streamlit"""
        
        pdf_bytes = self.generate_report(**kwargs)
        
        st.download_button(
            label="📥 Télécharger le Rapport PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf"
        )
```

---

À suivre dans le prochain message avec les seuils adaptatifs et l'intégration complète...