# scripts/train_ml_models.py
"""
Script d'entraînement des modèles ML
Utiliser pour entraînement batch avec données complètes
"""
import pandas as pd
import numpy as np
from core.module1 import DischargePredictor, create_features_from_weather

# 1. Charger données historiques
print("📊 Chargement données...")
# TODO: Charger vos vraies données
data = pd.read_csv('data/historical_weather_discharge.csv')

# 2. Feature engineering
print("🔧 Feature engineering...")
features = create_features_from_weather(data)
print(f"✅ {len(features.columns)} features créées")

# 3. Entraîner Random Forest
print("\n🌲 Entraînement Random Forest...")
rf_predictor = DischargePredictor(
    model_type='rf',
    lookback_days=30,
    forecast_horizon=10
)

metrics_rf = rf_predictor.train_random_forest(
    features,
    target_col='discharge',
    n_estimators=200,
    max_depth=20
)

print(f"✅ RF - R² = {metrics_rf['test_r2']:.3f}")
print(f"✅ RF - MSE = {metrics_rf['test_mse']:.2f}")

# Sauvegarder
rf_predictor.save_model('models/discharge_rf.pkl')
print("💾 Modèle RF sauvegardé")

# 4. Entraîner LSTM (si TensorFlow disponible)
try:
    print("\n🧠 Entraînement LSTM...")
    lstm_predictor = DischargePredictor(
        model_type='lstm',
        lookback_days=30,
        forecast_horizon=10
    )
    
    metrics_lstm = lstm_predictor.train_lstm(
        features,
        target_col='discharge',
        epochs=100,
        batch_size=32,
        validation_split=0.2
    )
    
    print(f"✅ LSTM - R² = {metrics_lstm['val_r2']:.3f}")
    print(f"✅ LSTM - MSE = {metrics_lstm['val_mse']:.2f}")
    
    # Sauvegarder
    lstm_predictor.save_model('models/discharge_lstm.pkl')
    print("💾 Modèle LSTM sauvegardé")

except ImportError:
    print("⚠️ TensorFlow non disponible - LSTM ignoré")

print("\n✅ Entraînement terminé !")