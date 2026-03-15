import os
import pandas as pd
from sqlalchemy import create_engine, text
from fpdf import FPDF
from datetime import datetime
from flask import Flask, send_file, request

app = Flask(__name__)

# --- FUNZIONE PER LEGGERE I DOCKER SECRETS ---
def get_secret(secret_name, default=None):
    try:
        with open(f'/run/secrets/{secret_name}', 'r') as f:
            return f.read().strip()
    except IOError:
        return os.getenv(secret_name.upper(), default)

# --- CONFIGURAZIONE ---
DB_USER = os.getenv('DB_USER', 'postgres')
DB_NAME = os.getenv('DB_NAME', 'medical_db')

# LETTURA DEI SEGRETI
DB_PASS = get_secret('db_password')       
DB_ENC_KEY = get_secret('db_key')         
APP_SECRET_KEY = get_secret('secret_key_auth')

HOST_PRIMARY = os.getenv('DB_HOST_PRIMARY', 'db-primary')
HOST_REPLICA = os.getenv('DB_HOST_REPLICA', 'db-replica')

def get_connection_string():
    # Usiamo DB_PASS letto dai segreti
    uri_primary = f"postgresql://{DB_USER}:{DB_PASS}@{HOST_PRIMARY}:5432/{DB_NAME}"
    uri_replica = f"postgresql://{DB_USER}:{DB_PASS}@{HOST_REPLICA}:5432/{DB_NAME}"
    
    try:
        print(f"Report Service: Provo connessione al MASTER...")
        engine = create_engine(uri_primary, connect_args={'connect_timeout': 2})
        with engine.connect() as conn:
            pass
        return uri_primary
    except:
        print(f"Report Service: MASTER giù. Uso REPLICA.")
        return uri_replica
    
def get_connection_string():
    """Failover Logic"""
    uri_primary = f"postgresql://{DB_USER}:{DB_PASS}@{HOST_PRIMARY}:5432/{DB_NAME}"
    uri_replica = f"postgresql://{DB_USER}:{DB_PASS}@{HOST_REPLICA}:5432/{DB_NAME}"
    
    try:
        print(f"Report Service: Provo connessione al MASTER...")
        engine = create_engine(uri_primary, connect_args={'connect_timeout': 2})
        with engine.connect() as conn:
            pass
        return uri_primary
    except:
        print(f"Report Service: MASTER giù. Uso REPLICA.")
        return uri_replica

def get_data(doctor_id):
    connection_string = get_connection_string()
    try:
        engine = create_engine(connection_string)
        
        # --- 2. QUERY CON DECRITTAZIONE ---
        query = text("""
        SELECT 
            u.username as medico, 
            p.id,
            pgp_sym_decrypt(p.full_name::bytea, :enc_key) as full_name, -- DECRITTAZIONE QUI
            p.age, p.sex, p.cp, p.trtbps, p.chol, 
            p.fbs, p.restecg, p.thalachh, p.exng, 
            p.oldpeak, p.slp, p.caa, p.thall
        FROM patients p
        JOIN users u ON p.doctor_id = u.username
        WHERE u.username = :doc_id
        ORDER BY full_name;
        """)
        
        with engine.connect() as conn:
            # --- 3. PASSAGGIO DELLA CHIAVE AI PARAMETRI ---
            df = pd.read_sql(query, conn, params={
                "doc_id": doctor_id,
                "enc_key": DB_ENC_KEY 
            })
            return df
    except Exception as e:
        print(f"ERRORE DB: {e}")
        return pd.DataFrame()

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Cartella Clinica - Report Medico', ln=True, align='C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Generato il: {datetime.now().strftime("%d/%m/%Y %H:%M")}', ln=True, align='C')
        self.ln(5)

    def chapter_body(self, df):
        if df.empty:
            self.set_font('Arial', '', 12)
            self.cell(0, 10, "Nessun paziente trovato per questo medico.", ln=True)
            return

        # Recupero del nome del medico dal primo record
        medico = df.iloc[0]['medico']
        
        # Intestazione Medico
        self.set_fill_color(50, 50, 100)
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, f" Dr. {medico} - Pazienti in carico: {len(df)}", ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(5)

        # Scheda per ogni paziente
        for _, row in df.iterrows():
            self.print_patient_card(row)
            self.ln(5)

    def print_patient_card(self, row):
        self.set_fill_color(245, 245, 245)
        self.rect(self.get_x(), self.get_y(), 190, 45, 'F')
        
        self.set_font('Arial', 'B', 12)
        # Qui row['full_name'] sarà leggibile grazie alla query SQL decriptata
        self.cell(0, 8, f"Paziente: {row['full_name']} (ID: {row['id']})", ln=True)
        
        self.set_font('Arial', '', 10)
        
        sesso = "M" if row['sex'] == 1 else "F"
        # Gestione sicura CP (evita crash index out of bound)
        cp_val = int(row['cp'])
        cp_labels = ["Asint.", "Atipica", "Non Angin.", "Asint."]
        cp_txt = cp_labels[cp_val] if 0 <= cp_val < len(cp_labels) else str(cp_val)
        
        self.cell(45, 6, f"Eta': {row['age']} | Sesso: {sesso}", 0)
        self.cell(45, 6, f"Pressione: {row['trtbps']} mmHg", 0)
        self.cell(45, 6, f"Colesterolo: {row['chol']}", 0)
        self.cell(45, 6, f"Dolore Petto: {cp_txt}", 0, 1)
        
        fbs = "Si" if row['fbs'] == 1 else "No"
        exng = "Si" if row['exng'] == 1 else "No"
        
        self.cell(45, 6, f"Glicemia >120: {fbs}", 0)
        self.cell(45, 6, f"Max Battito: {row['thalachh']}", 0)
        self.cell(45, 6, f"Angina Sforzo: {exng}", 0)
        self.cell(45, 6, f"ECG Riposo: {row['restecg']}", 0, 1)
        
        self.cell(45, 6, f"Oldpeak: {row['oldpeak']}", 0)
        self.cell(45, 6, f"Slope: {row['slp']}", 0)
        self.cell(45, 6, f"Vasi (CAA): {row['caa']}", 0)
        self.cell(45, 6, f"Thallium: {row['thall']}", 0, 1)
        
        self.ln(5)

@app.route('/generate_report', methods=['GET'])
def generate_report():
    doctor_id = request.args.get('doctor_id')
    
    if not doctor_id:
        return "Errore: Medico non specificato", 400

    print(f"Generazione report per Medico: {doctor_id}")
    
    df = get_data(doctor_id)
    
    pdf = PDFReport()
    pdf.add_page()
    pdf.chapter_body(df)
    
    output_path = f"/tmp/report_{doctor_id}.pdf"
    pdf.output(output_path)
    
    return send_file(output_path, as_attachment=True, download_name=f'report_{doctor_id}.pdf')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002)