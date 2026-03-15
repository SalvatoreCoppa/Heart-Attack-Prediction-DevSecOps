from flask import Flask, request, jsonify
import joblib
import pandas as pd
import os
import jwt
from functools import wraps

app = Flask(__name__)

# --- CONFIGURAZIONE DINAMICA ---
# Prende le variabili dal docker-compose, altrimenti usa i default
DB_USER = os.getenv('DB_USER', 'postgres')     
DB_PASS = os.getenv('DB_PASSWORD', 'password_segreta')
DB_HOST = os.getenv('DB_HOST', 'db-primary')   # Punta al MASTER
DB_NAME = os.getenv('DB_NAME', 'medical_db')  

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'super-segreto-universitario')

# La stringa di connessione userà i valori corretti
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# --- Percorsi dei modelli nel container ---
MODEL_PATH = 'models/model.joblib'
SCALER_PATH = 'models/scaler.joblib'

print("Caricamento modelli...")
try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("Modelli caricati con successo!")
except Exception as e:
    print(f"ERRORE GRAVE: Impossibile caricare i modelli. {e}")
    model = None
    scaler = None
SECRET_KEY = os.getenv('SECRET_KEY', 'super-segreto-universitario')

# --- Decoratore per proteggere le rotte ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Cerca il token nell'header della richiesta (Authorization: Bearer <token>)
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token mancante!'}), 401
        
        try:
            # Verifica la firma del token
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except:
            return jsonify({'message': 'Token invalido o scaduto!'}), 401
        
        return f(*args, **kwargs)
    return decorated

# --- Applica la protezione alla rotta predict ---
@app.route('/predict', methods=['POST'])
def predict():
    if not model or not scaler:
        return jsonify({'error': 'Model not loaded'}), 500

    try:
        data = request.get_json()
        
        # Le colonne devono essere nello stesso ordine dell'addestramento
        feat_cols = [
            'age', 'sex', 'cp', 'trtbps', 'chol', 'fbs', 'restecg',
            'thalachh', 'exng', 'oldpeak', 'slp', 'caa', 'thall'
        ]
        
        # Creazione del DataFrame
        df = pd.DataFrame([data['features']], columns=feat_cols)

        # Uso dello scaler e poi del modello
        X = scaler.transform(df)
        prediction = model.predict(X)
        
        result_class = int(prediction[0])
        
        return jsonify({
            'prediction': result_class,
            'message': "High probability of Heart Attack" if result_class == 1 else "Low probability"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    # Flask deve ascoltare su 0.0.0.0
    app.run(host='0.0.0.0', port=5000)