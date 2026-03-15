import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import joblib
import os

# 1. Carica i dati
try:
    df = pd.read_csv('heart.csv')
    print("Dataset caricato correttamente.")
except FileNotFoundError:
    print("Errore: File 'data/heart.csv' non trovato.")
    exit()

# 2. Prepara i dati (X e y)
feat_cols = [
    'age', 'sex', 'cp', 'trtbps', 'chol', 'fbs', 'restecg',
    'thalachh', 'exng', 'oldpeak', 'slp', 'caa', 'thall'
]
target_col = 'output' 

X = df[feat_cols]
y = df[target_col]

# 3. Divide in Training e Test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Crea Scaler e Modello
scaler = StandardScaler()
model = RandomForestClassifier(n_estimators=100, random_state=42)

print("Addestramento in corso...")

# Fit dello Scaler
X_train_scaled = scaler.fit_transform(X_train)

# Fit del Modello
model.fit(X_train_scaled, y_train)

print(f"Addestramento completato. Accuratezza sul train: {model.score(X_train_scaled, y_train):.2f}")

# 5. Salva i file .joblib
if not os.path.exists('backend/models'):
    os.makedirs('backend/models')

print("Salvataggio file...")
joblib.dump(model, 'backend/models/model.joblib')
joblib.dump(scaler, 'backend/models/scaler.joblib')

print("Fatto! I file model.joblib e scaler.joblib sono pronti in backend/models/")