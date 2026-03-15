import time
import os
import datetime
import jwt
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy 
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy import create_engine, text

app = Flask(__name__)

# --- FUNZIONE PER LEGGERE I DOCKER SECRETS ---
def get_secret(secret_name, default=None):
    try:
        with open(f'/run/secrets/{secret_name}', 'r') as f:
            val = f.read().strip()
            if val: 
                print(f"🔓 Segreto '{secret_name}' caricato correttamente!")
                return val
    except IOError:
        pass
    print(f"⚠️ Segreto '{secret_name}' non trovato nei file, cerco in ENV...")
    return os.getenv(secret_name.upper(), default)

# --- CONFIGURAZIONE ---
DB_USER = os.getenv('DB_USER', 'postgres')
DB_NAME = os.getenv('DB_NAME', 'medical_db')

DB_PASS = get_secret('db_password', 'password_segreta')
DB_ENC_KEY = get_secret('db_key', default=None)

if not DB_ENC_KEY or len(DB_ENC_KEY) < 32:
    print("🔥 ERRORE CRITICO: La chiave di crittografia (DB_ENC_KEY) è VUOTA o non valida!")

HOST_PRIMARY = os.getenv('DB_HOST_PRIMARY', 'db-primary')
HOST_REPLICA = os.getenv('DB_HOST_REPLICA', 'db-replica')

URI_PRIMARY = f'postgresql://{DB_USER}:{DB_PASS}@{HOST_PRIMARY}/{DB_NAME}'
URI_REPLICA = f'postgresql://{DB_USER}:{DB_PASS}@{HOST_REPLICA}/{DB_NAME}'

app.config['SQLALCHEMY_DATABASE_URI'] = URI_PRIMARY
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = get_secret('secret_key_auth', 'super-segreto')

db = SQLAlchemy(app)

# --- OTTIMIZZAZIONE DATABASE (Global Engines & Circuit Breaker) ---
# Creiamo gli engine UNA VOLTA SOLA per sfruttare il Connection Pooling.
# pool_pre_ping=True scarta le connessioni vecchie/rotte automaticamente.
engine_primary = create_engine(URI_PRIMARY, pool_pre_ping=True, connect_args={'connect_timeout': 2})
engine_replica = create_engine(URI_REPLICA, pool_pre_ping=True, connect_args={'connect_timeout': 2})

# Variabili per gestire il "Circuit Breaker"
PRIMARY_DOWN_TIMESTAMP = 0
RETRY_PRIMARY_AFTER_SECONDS = 30  # Secondi di attesa prima di riprovare il Master dopo un fallimento

# --- MODELLI ---
class User(db.Model):
    __tablename__ = 'users'
    username = db.Column(db.String(50), primary_key=True)
    password = db.Column(db.Text, nullable=False)
    patients = db.relationship('Patient', backref='doctor', lazy=True)

class Patient(db.Model):
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.String(50), db.ForeignKey('users.username'), nullable=False)
    full_name = db.Column(db.LargeBinary) 
    age = db.Column(db.Integer)
    sex = db.Column(db.Integer)
    cp = db.Column(db.Integer) #dolore toracico
    trtbps = db.Column(db.Integer) #pressione a riposo
    chol = db.Column(db.Integer) #colesterolo
    fbs = db.Column(db.Integer) #glicemia a digiuno
    restecg = db.Column(db.Integer) #ECG a riposo
    thalachh = db.Column(db.Integer) 
    exng = db.Column(db.Integer) #angina da sforzo
    oldpeak = db.Column(db.Float)
    slp = db.Column(db.Integer)
    caa = db.Column(db.Integer)
    thall = db.Column(db.Integer)
    prediction_result = db.Column(db.Integer)
    visit_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    fiscal_code = db.Column(db.LargeBinary)

class SimpleUser:
    def __init__(self, username):
        self.username = username

# --- HELPERS DATABASE ---

def wait_for_db():
    print("⏳ Attesa avvio Database Master...")
    while True:
        try:
            # Usiamo l'engine globale
            with engine_primary.connect() as conn:
                print("✅ Database Master Connesso!")
                return
        except:
            print("... DB non ancora pronto, riprovo tra 2s ...")
            time.sleep(2)

def _query_replica(sql, params):
    """Funzione interna per interrogare la replica"""
    try:
        with engine_replica.connect() as conn:
            return conn.execute(text(sql), params).fetchall()
    except Exception as e:
        print(f"❌ Read Replica Fallito: {e}")
        raise e

def execute_read_query(sql, params):
    global PRIMARY_DOWN_TIMESTAMP
    
    params['enc_key'] = DB_ENC_KEY
    current_time = time.time()

    # 1. CIRCUIT BREAKER: Se il master è fallito di recente, andiamo SUBITO alla replica
    if current_time - PRIMARY_DOWN_TIMESTAMP < RETRY_PRIMARY_AFTER_SECONDS:
        # print("⚡ Circuit Breaker attivo: vado diretto alla Replica") 
        return _query_replica(sql, params)

    # 2. Tentativo Master
    try:
        with engine_primary.connect() as conn:
            return conn.execute(text(sql), params).fetchall()
    except Exception as e:
        print(f"⚠️ Master Read Fallito (Timeout/Error). Attivo Circuit Breaker per {RETRY_PRIMARY_AFTER_SECONDS}s.")
        PRIMARY_DOWN_TIMESTAMP = time.time() # Segniamo l'ora del guasto
        
        # 3. Fallback su Replica
        return _query_replica(sql, params)

def save_patient_primary_only(new_patient_obj):
    if not DB_ENC_KEY:
        return False, "Errore interno: Chiave crittografia mancante"

    new_patient_obj['enc_key'] = DB_ENC_KEY
    
    insert_sql = """
        INSERT INTO patients (
            doctor_id, full_name, fiscal_code, age, sex, cp, trtbps, chol, fbs, restecg, 
            thalachh, exng, oldpeak, slp, caa, thall, prediction_result, visit_date
        )
        VALUES (
            :doc, 
            pgp_sym_encrypt(:name, :enc_key), 
            pgp_sym_encrypt(:cf, :enc_key), 
            :age, :sex, :cp, :trtbps, :chol, :fbs, :restecg, 
            :thal, :exng, :old, :slp, :caa, :thall, :pred, 
            :v_date 
        )
    """

    try:
        # Usiamo l'engine globale
        with engine_primary.connect() as conn:
            conn.execute(text(insert_sql), new_patient_obj)
            conn.commit()
        return True, "Referto salvato correttamente"
    except Exception as e:
        print(f"⚠️ ERRORE SCRITTURA MASTER: {e}")
        return False, "Impossibile salvare: Attendere il ripristino del servizio da parte dei tecnici, ci scusiamo per il disagio "
    
# --- DECORATORE AUTH ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token: return jsonify({'message': 'Token mancante!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            username = data['user']
            rows = execute_read_query("SELECT username FROM users WHERE username = :u", {"u": username})
            if not rows: raise Exception("Utente non trovato")
            current_user = SimpleUser(username=rows[0][0])
        except Exception as e:
            return jsonify({'message': f'Token invalido o DB Error: {str(e)}'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# --- ROTTE ---

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    try:
        rows = execute_read_query("SELECT username, password FROM users WHERE username = :u", {"u": username})
        if not rows: return jsonify({'message': 'Utente non trovato'}), 401
        
        user_data = rows[0]
        if check_password_hash(user_data[1], password):
            token = jwt.encode({'user': user_data[0], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, app.config['SECRET_KEY'], algorithm="HS256")
            return jsonify({'token': token})
            
    except Exception as e:
        return jsonify({'message': f'Errore: {str(e)}'}), 500
    return jsonify({'message': 'Credenziali errate'}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    try:
        if execute_read_query("SELECT username FROM users WHERE username = :u", {"u": username}):
            return jsonify({'message': 'Medico già esistente'}), 400
        
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Scrittura: usiamo engine_primary globale
        with engine_primary.connect() as conn:
            conn.execute(text("INSERT INTO users (username, password) VALUES (:u, :p)"), {"u": username, "p": hashed_pw})
            conn.commit()
            
        return jsonify({'message': 'Medico registrato con successo!'}), 200
    except Exception as e:
        return jsonify({'message': f'Errore: {str(e)}'}), 500

@app.route('/patients', methods=['GET'])
@token_required
def get_patients(current_user):
    try:
        sql = """
            SELECT id, doctor_id, 
            pgp_sym_decrypt(full_name::bytea, :enc_key) as full_name_decrypted,
            pgp_sym_decrypt(fiscal_code::bytea, :enc_key) as cf_decrypted,
            age, sex, cp, trtbps, chol, fbs, restecg, thalachh, exng, oldpeak, slp, caa, thall,
            prediction_result, visit_date
            FROM patients WHERE doctor_id = :doc
            ORDER BY visit_date DESC
        """
        rows = execute_read_query(sql, {"doc": current_user.username})
        patients_list = []
        for row in rows:
            nome = row.full_name_decrypted if row.full_name_decrypted else "N/D"
            cf = row.cf_decrypted if row.cf_decrypted else "N/D"
            
            p = {
                'id': row.id, 'doctor_id': row.doctor_id, 
                'full_name': nome, 
                'fiscal_code': cf,
                'age': row.age, 'sex': row.sex, 'cp': row.cp, 'trtbps': row.trtbps,
                'chol': row.chol, 'fbs': row.fbs, 'restecg': row.restecg, 
                'thalachh': row.thalachh, 'exng': row.exng, 'oldpeak': row.oldpeak,
                'slp': row.slp, 'caa': row.caa, 'thall': row.thall,
                'prediction': row.prediction_result,
                'date': str(row.visit_date)
            }
            patients_list.append(p)
        return jsonify(patients_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/patients', methods=['POST'])
@token_required
def add_patient(current_user):
    data = request.get_json()
    
    prediction_val = data.get('prediction', None)
    fiscal_code_val = data.get('fiscal_code', 'N/D')
    
    manual_date = data.get('visit_date')
    if not manual_date:
        manual_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    p_data = {
        'doc': current_user.username,
        'name': data['full_name'], 
        'cf': fiscal_code_val,
        'age': data['age'], 'sex': data['sex'],
        'cp': data['cp'], 'trtbps': data['trtbps'], 'chol': data['chol'], 
        'fbs': data['fbs'], 'restecg': data['restecg'], 'thal': data['thalachh'], 
        'exng': data['exng'], 'old': data['oldpeak'], 'slp': data['slp'], 
        'caa': data['caa'], 'thall': data['thall'],
        'pred': prediction_val,
        'v_date': manual_date
    }
    
    success, msg = save_patient_primary_only(p_data)
    if success: return jsonify({'message': msg}), 200
    return jsonify({'error': msg}), 500

@app.route('/patients/<int:patient_id>', methods=['DELETE'])
@token_required
def delete_patient(current_user, patient_id):
    try:
        # Scrittura: usiamo engine_primary globale
        with engine_primary.connect() as conn:
            sql = text("DELETE FROM patients WHERE id = :pid AND doctor_id = :doc")
            result = conn.execute(sql, {"pid": patient_id, "doc": current_user.username})
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'message': 'Paziente non trovato o non autorizzato'}), 404
                
        return jsonify({'message': 'Paziente eliminato con successo'}), 200

    except Exception as e:
        print(f"Errore Delete: {e}")
        return jsonify({'error': str(e)}), 500

# --- AVVIO ---
if __name__ == '__main__':
    wait_for_db()
    with app.app_context():
        try:
            # Creazione estensione e tabelle
            with engine_primary.connect() as conn:
                 conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
                 conn.commit()
            
            db.create_all()
            print("Init DB completato.")
        except Exception as e:
            print(f"Errore Init (non bloccante): {e}")

    app.run(host='0.0.0.0', port=5001)