# core/module1/ml_predictions.py
"""
Modèles Machine Learning pour prévisions hydrologiques avancées
LSTM (séries temporelles) + Random Forest (classification risques)
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta
import pickle
import json
from pathlib import Path

# Machine Learning
try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import accuracy_score, mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn non disponible - Fonctionnalités ML limitées")

# Deep Learning (optionnel)
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, callbacks
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠️ TensorFlow non disponible - LSTM désactivé")


class DischargePredictor:
    """
    Prédicteur de débit utilisant Machine Learning
    Combine LSTM (deep learning) et Random Forest
    """
    
    def __init__(
        self,
        model_type: str = 'ensemble',  # 'lstm', 'rf', 'ensemble'
        lookback_days: int = 30,
        forecast_horizon: int = 10
    ):
        """
        Initialise le prédicteur
        
        Args:
            model_type: Type de modèle ('lstm', 'rf', 'ensemble')
            lookback_days: Nombre de jours d'historique pour prédiction
            forecast_horizon: Horizon de prévision (jours)
        """
        self.model_type = model_type
        self.lookback_days = lookback_days
        self.forecast_horizon = forecast_horizon
        
        # Modèles
        self.lstm_model = None
        self.rf_model = None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        
        # Métadonnées
        self.is_trained = False
        self.feature_names = []
        self.training_history = {}
    
    def create_lstm_model(
        self,
        n_features: int,
        lstm_units: List[int] = [128, 64, 32],
        dropout_rate: float = 0.2
    ) -> 'keras.Model':
        """
        Crée un modèle LSTM pour prévision de séries temporelles
        
        Args:
            n_features: Nombre de features d'entrée
            lstm_units: Unités par couche LSTM
            dropout_rate: Taux de dropout
        
        Returns:
            Modèle Keras compilé
        """
        
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow requis pour LSTM")
        
        model = models.Sequential([
            # Couche d'entrée
            layers.Input(shape=(self.lookback_days, n_features)),
            
            # LSTM layers avec dropout
            layers.LSTM(lstm_units[0], return_sequences=True),
            layers.Dropout(dropout_rate),
            
            layers.LSTM(lstm_units[1], return_sequences=True),
            layers.Dropout(dropout_rate),
            
            layers.LSTM(lstm_units[2], return_sequences=False),
            layers.Dropout(dropout_rate),
            
            # Dense layers
            layers.Dense(64, activation='relu'),
            layers.Dropout(dropout_rate),
            
            layers.Dense(32, activation='relu'),
            
            # Output layer (prévision multi-horizon)
            layers.Dense(self.forecast_horizon)
        ])
        
        # Compilation
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae', 'mse']
        )
        
        return model
    
    def prepare_sequences(
        self,
        data: pd.DataFrame,
        target_col: str = 'discharge'
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prépare les séquences pour LSTM
        
        Args:
            data: DataFrame avec features
            target_col: Colonne cible
        
        Returns:
            (X, y) - Séquences d'entrée et sorties
        """
        
        # Features
        feature_cols = [c for c in data.columns if c != target_col]
        self.feature_names = feature_cols
        
        X_data = data[feature_cols].values
        y_data = data[target_col].values
        
        X_sequences = []
        y_sequences = []
        
        # Créer séquences glissantes
        for i in range(len(data) - self.lookback_days - self.forecast_horizon + 1):
            # Séquence d'entrée (lookback_days jours)
            X_seq = X_data[i:i + self.lookback_days]
            
            # Sortie (forecast_horizon jours futurs)
            y_seq = y_data[i + self.lookback_days:i + self.lookback_days + self.forecast_horizon]
            
            if len(y_seq) == self.forecast_horizon:
                X_sequences.append(X_seq)
                y_sequences.append(y_seq)
        
        return np.array(X_sequences), np.array(y_sequences)
    
    def train_lstm(
        self,
        data: pd.DataFrame,
        target_col: str = 'discharge',
        validation_split: float = 0.2,
        epochs: int = 100,
        batch_size: int = 32,
        verbose: int = 1
    ) -> Dict:
        """
        Entraîne le modèle LSTM
        
        Args:
            data: DataFrame avec historique
            target_col: Colonne cible
            validation_split: Part des données pour validation
            epochs: Nombre d'epochs
            batch_size: Taille des batchs
            verbose: Verbosité
        
        Returns:
            Historique d'entraînement
        """
        
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow requis")
        
        # Préparer données
        X, y = self.prepare_sequences(data, target_col)
        
        # Normaliser
        n_samples, n_timesteps, n_features = X.shape
        X_reshaped = X.reshape(-1, n_features)
        X_scaled = self.scaler.fit_transform(X_reshaped)
        X = X_scaled.reshape(n_samples, n_timesteps, n_features)
        
        # Split train/val
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, shuffle=False
        )
        
        # Créer modèle
        self.lstm_model = self.create_lstm_model(n_features)
        
        # Callbacks
        early_stop = callbacks.EarlyStopping(
            monitor='val_loss',
            patience=15,
            restore_best_weights=True
        )
        
        reduce_lr = callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6
        )
        
        # Entraînement
        history = self.lstm_model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop, reduce_lr],
            verbose=verbose
        )
        
        self.is_trained = True
        self.training_history['lstm'] = history.history
        
        # Évaluation
        y_pred = self.lstm_model.predict(X_val, verbose=0)
        mse = mean_squared_error(y_val, y_pred)
        r2 = r2_score(y_val.flatten(), y_pred.flatten())
        
        return {
            'history': history.history,
            'val_mse': float(mse),
            'val_r2': float(r2),
            'best_epoch': len(history.history['loss']) - early_stop.patience
        }
    
    def train_random_forest(
        self,
        data: pd.DataFrame,
        target_col: str = 'discharge',
        n_estimators: int = 100,
        max_depth: int = 20
    ) -> Dict:
        """
        Entraîne Random Forest pour prévision
        
        Args:
            data: DataFrame avec features
            target_col: Colonne cible
            n_estimators: Nombre d'arbres
            max_depth: Profondeur max
        
        Returns:
            Métriques d'entraînement
        """
        
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn requis")
        
        # Préparer données
        feature_cols = [c for c in data.columns if c != target_col]
        self.feature_names = feature_cols
        
        X = data[feature_cols].values
        y = data[target_col].values
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Normaliser
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Entraîner
        self.rf_model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1
        )
        
        self.rf_model.fit(X_train_scaled, y_train)
        
        # Évaluation
        y_pred = self.rf_model.predict(X_test_scaled)
        
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.rf_model, X_train_scaled, y_train,
            cv=5, scoring='r2'
        )
        
        self.is_trained = True
        self.training_history['rf'] = {
            'test_mse': float(mse),
            'test_r2': float(r2),
            'cv_r2_mean': float(cv_scores.mean()),
            'cv_r2_std': float(cv_scores.std())
        }
        
        return self.training_history['rf']
    
    def predict(
        self,
        recent_data: pd.DataFrame,
        method: str = 'auto'
    ) -> Dict:
        """
        Fait une prévision de débit
        
        Args:
            recent_data: Données récentes (lookback_days derniers jours)
            method: Méthode ('lstm', 'rf', 'ensemble', 'auto')
        
        Returns:
            Prévisions avec intervalles de confiance
        """
        
        if not self.is_trained:
            raise ValueError("Modèle non entraîné")
        
        # Auto-sélection méthode
        if method == 'auto':
            if self.model_type == 'ensemble':
                method = 'ensemble'
            elif self.lstm_model is not None:
                method = 'lstm'
            else:
                method = 'rf'
        
        predictions = {}
        
        # LSTM
        if method in ['lstm', 'ensemble'] and self.lstm_model is not None:
            X = recent_data[self.feature_names].values[-self.lookback_days:]
            X_scaled = self.scaler.transform(X)
            X_seq = X_scaled.reshape(1, self.lookback_days, -1)
            
            pred_lstm = self.lstm_model.predict(X_seq, verbose=0)[0]
            predictions['lstm'] = pred_lstm
        
        # Random Forest (prédiction récursive)
        if method in ['rf', 'ensemble'] and self.rf_model is not None:
            pred_rf = []
            current_data = recent_data[self.feature_names].values[-1:]
            
            for _ in range(self.forecast_horizon):
                X_scaled = self.scaler.transform(current_data)
                pred = self.rf_model.predict(X_scaled)[0]
                pred_rf.append(pred)
                # Update features (simplified)
                current_data = X_scaled
            
            predictions['rf'] = np.array(pred_rf)
        
        # Ensemble (moyenne pondérée)
        if method == 'ensemble' and 'lstm' in predictions and 'rf' in predictions:
            # 60% LSTM, 40% RF (LSTM généralement meilleur sur séries temporelles)
            predictions['ensemble'] = 0.6 * predictions['lstm'] + 0.4 * predictions['rf']
        
        # Sélectionner prédiction finale
        if method == 'ensemble' and 'ensemble' in predictions:
            final_pred = predictions['ensemble']
        elif method == 'lstm' and 'lstm' in predictions:
            final_pred = predictions['lstm']
        elif 'rf' in predictions:
            final_pred = predictions['rf']
        else:
            raise ValueError(f"Méthode {method} non disponible")
        
        # Intervalles de confiance (approximation)
        # Basé sur variance du modèle
        std_dev = np.std(final_pred) if len(final_pred) > 1 else final_pred.mean() * 0.15
        
        return {
            'predictions': final_pred.tolist(),
            'lower_bound': (final_pred - 1.96 * std_dev).tolist(),
            'upper_bound': (final_pred + 1.96 * std_dev).tolist(),
            'confidence': 0.95,
            'method': method,
            'individual_predictions': predictions
        }
    
    def save_model(self, filepath: str):
        """Sauvegarde le modèle"""
        
        model_data = {
            'model_type': self.model_type,
            'lookback_days': self.lookback_days,
            'forecast_horizon': self.forecast_horizon,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained,
            'training_history': self.training_history
        }
        
        # Sauvegarder LSTM
        if self.lstm_model is not None and TF_AVAILABLE:
            lstm_path = filepath.replace('.pkl', '_lstm.h5')
            self.lstm_model.save(lstm_path)
            model_data['lstm_path'] = lstm_path
        
        # Sauvegarder RF et scaler
        if self.rf_model is not None and SKLEARN_AVAILABLE:
            model_data['rf_model'] = self.rf_model
            model_data['scaler'] = self.scaler
        
        # Pickle
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    @classmethod
    def load_model(cls, filepath: str) -> 'DischargePredictor':
        """Charge un modèle sauvegardé"""
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        # Recréer prédicteur
        predictor = cls(
            model_type=model_data['model_type'],
            lookback_days=model_data['lookback_days'],
            forecast_horizon=model_data['forecast_horizon']
        )
        
        predictor.feature_names = model_data['feature_names']
        predictor.is_trained = model_data['is_trained']
        predictor.training_history = model_data['training_history']
        
        # Charger LSTM
        if 'lstm_path' in model_data and TF_AVAILABLE:
            predictor.lstm_model = keras.models.load_model(model_data['lstm_path'])
        
        # Charger RF
        if 'rf_model' in model_data:
            predictor.rf_model = model_data['rf_model']
            predictor.scaler = model_data['scaler']
        
        return predictor


class RiskClassifier:
    """
    Classificateur de risque (ML)
    Prédit niveau de risque (low/moderate/high/critical)
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.feature_names = []
        self.risk_labels = ['low', 'moderate', 'high', 'critical']
        self.is_trained = False
    
    def train(
        self,
        data: pd.DataFrame,
        target_col: str = 'risk_level',
        n_estimators: int = 200,
        max_depth: int = 15
    ) -> Dict:
        """
        Entraîne classificateur de risque
        
        Args:
            data: DataFrame avec features et risk_level
            target_col: Colonne cible
            n_estimators: Nombre d'arbres
            max_depth: Profondeur max
        
        Returns:
            Métriques d'entraînement
        """
        
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn requis")
        
        # Préparer données
        feature_cols = [c for c in data.columns if c != target_col]
        self.feature_names = feature_cols
        
        X = data[feature_cols].values
        y = data[target_col].values
        
        # Encoder labels
        label_map = {label: i for i, label in enumerate(self.risk_labels)}
        y_encoded = np.array([label_map[label] for label in y])
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )
        
        # Normaliser
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Entraîner
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Évaluation
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X_train_scaled, y_train,
            cv=5, scoring='accuracy'
        )
        
        # Importance des features
        feature_importance = dict(zip(
            self.feature_names,
            self.model.feature_importances_
        ))
        
        self.is_trained = True
        
        return {
            'accuracy': float(accuracy),
            'cv_accuracy_mean': float(cv_scores.mean()),
            'cv_accuracy_std': float(cv_scores.std()),
            'feature_importance': feature_importance
        }
    
    def predict(self, features: pd.DataFrame) -> Dict:
        """
        Prédit niveau de risque
        
        Args:
            features: DataFrame avec features
        
        Returns:
            Prédiction avec probabilités
        """
        
        if not self.is_trained:
            raise ValueError("Modèle non entraîné")
        
        X = features[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        
        # Prédiction
        pred_encoded = self.model.predict(X_scaled)
        pred_proba = self.model.predict_proba(X_scaled)
        
        # Décoder
        pred_labels = [self.risk_labels[p] for p in pred_encoded]
        
        probabilities = {
            label: float(prob)
            for label, prob in zip(self.risk_labels, pred_proba[0])
        }
        
        return {
            'risk_level': pred_labels[0],
            'confidence': float(pred_proba[0][pred_encoded[0]]),
            'probabilities': probabilities
        }


def create_features_from_weather(
    weather_data: pd.DataFrame
) -> pd.DataFrame:
    """
    Crée features ML à partir de données météo
    
    Args:
        weather_data: DataFrame avec température, précip, vent, etc.
    
    Returns:
        DataFrame avec features enrichies
    """
    
    df = weather_data.copy()
    
    # Features temporelles
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_year'] = df['date'].dt.dayofyear
        df['month'] = df['date'].dt.month
        df['week'] = df['date'].dt.isocalendar().week
    
    # Features cumulatives
    for window in [7, 14, 30]:
        if 'precipitation_sum' in df.columns:
            df[f'precip_cumsum_{window}d'] = df['precipitation_sum'].rolling(window, min_periods=1).sum()
            df[f'precip_mean_{window}d'] = df['precipitation_sum'].rolling(window, min_periods=1).mean()
        
        if 'temperature_2m_max' in df.columns:
            df[f'temp_mean_{window}d'] = df['temperature_2m_max'].rolling(window, min_periods=1).mean()
    
    # Streak de jours secs
    if 'precipitation_sum' in df.columns:
        df['is_dry'] = (df['precipitation_sum'] < 1).astype(int)
        df['dry_streak'] = df['is_dry'].groupby((df['is_dry'] != df['is_dry'].shift()).cumsum()).cumsum()
    
    # Différences
    if 'temperature_2m_max' in df.columns:
        df['temp_diff'] = df['temperature_2m_max'].diff()
    
    if 'precipitation_sum' in df.columns:
        df['precip_diff'] = df['precipitation_sum'].diff()
    
    # Indicateurs dérivés
    if 'temperature_2m_max' in df.columns and 'precipitation_sum' in df.columns:
        # Évapotranspiration simplifiée (Hargreaves)
        df['et0'] = 0.0023 * df['temperature_2m_max'] * 17.8
        df['water_deficit'] = df['et0'] - df['precipitation_sum']
    
    # Remplir NaN
    df = df.fillna(method='bfill').fillna(0)
    
    return df


# Exemple d'utilisation
def example_usage():
    """
    Exemple d'utilisation des modèles ML
    """
    
    print("=== Exemple ML pour Prévision Hydrologique ===\n")
    
    # 1. Créer données synthétiques
    dates = pd.date_range('2022-01-01', '2024-12-31', freq='D')
    n_days = len(dates)
    
    # Simuler données météo
    np.random.seed(42)
    weather_data = pd.DataFrame({
        'date': dates,
        'precipitation_sum': np.random.gamma(2, 10, n_days),
        'temperature_2m_max': 25 + 5 * np.sin(np.arange(n_days) * 2 * np.pi / 365) + np.random.normal(0, 2, n_days),
        'wind_speed_10m_max': np.random.gamma(3, 5, n_days)
    })
    
    # Simuler débit (corrélé avec précip)
    weather_data['discharge'] = (
        weather_data['precipitation_sum'] * 0.8 + 
        np.random.normal(0, 5, n_days) +
        50
    )
    
    # 2. Créer features
    print("Création des features...")
    features_df = create_features_from_weather(weather_data)
    print(f"✅ {len(features_df.columns)} features créées\n")
    
    # 3. Entraîner modèle
    if SKLEARN_AVAILABLE:
        print("Entraînement Random Forest...")
        predictor = DischargePredictor(model_type='rf', lookback_days=30, forecast_horizon=10)
        
        metrics = predictor.train_random_forest(features_df, target_col='discharge')
        print(f"✅ R² = {metrics['test_r2']:.3f}")
        print(f"✅ MSE = {metrics['test_mse']:.2f}\n")
        
        # 4. Faire prédiction
        print("Prédiction sur 10 jours...")
        recent = features_df.iloc[-30:]
        forecast = predictor.predict(recent, method='rf')
        
        print(f"✅ Prévisions : {[f'{x:.1f}' for x in forecast['predictions'][:5]]}... m³/s")
        print(f"✅ Intervalle confiance : 95%\n")
    
    print("Exemple terminé !")


if __name__ == '__main__':
    example_usage()