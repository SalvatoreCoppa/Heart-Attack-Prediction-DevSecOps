import streamlit as st
import requests
from PIL import Image
import os
import time

# CONFIGURAZIONE URL
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
AUTH_URL = os.getenv('AUTH_URL', 'http://localhost:5001')
REPORT_URL = os.getenv('REPORT_URL', 'http://localhost:5002')

st.set_page_config(page_title="HeartAttackPredictionApp", layout="wide")

# --- GESTIONE LOGIN ---
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'username' not in st.session_state:
    st.session_state.username = None

# --- FUNZIONE LOGIN PAGE PROFESSIONAL ---
def login_page():
    st.markdown("""
    <style>
        .title-text { text-align: center; color: #2c3e50; font-size: 2.5em; font-weight: 600; margin-bottom: 0px; }
        .subtitle-text { text-align: center; color: #7f8c8d; font-size: 1.1em; margin-bottom: 30px; }
        .stButton button { width: 100%; border-radius: 6px; height: 45px; font-weight: 500; }
        .stTextInput input { border-radius: 4px; }
        .stTabs [data-baseweb="tab-list"] { gap: 20px; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

    col_spacer_l, col_main, col_spacer_r = st.columns([1, 1.5, 1])

    with col_main:
        try:
            image = Image.open('data/heart_attack.png')
            c_img_1, c_img_2, c_img_3 = st.columns([1,1,1])
            with c_img_2:
                st.image(image, use_container_width=True) 
        except:
            pass 

        st.markdown('<div class="title-text">HeartAttackPredictionApp</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle-text">Sistema di Supporto Decisionale & Gestione Pazienti</div>', unsafe_allow_html=True)

        with st.container(border=True):
            tab1, tab2 = st.tabs(["Accedi", "Registrazione Medico"])
            
            with tab1:
                st.write("") 
                user = st.text_input("Identificativo Utente", key="l_u", placeholder="Inserire username")
                pw = st.text_input("Password", type="password", key="l_p")

                st.write("") 
                if st.button("Accedi al sistema", type="primary"):
                    if not user or not pw:
                        st.warning("Inserire le credenziali di accesso.")
                    else:
                        with st.spinner("Autenticazione in corso..."):
                            try:
                                payload = {'username': user, 'password': pw}
                                response = requests.post(f"{AUTH_URL}/login", json=payload)
                                
                                if response.status_code == 200:
                                    token = response.json().get('token')
                                    st.session_state.auth_token = token
                                    st.session_state.username = user
                                    st.toast("Autenticazione riuscita", icon="✅")
                                    time.sleep(0.5) 
                                    st.rerun()
                                elif response.status_code == 401:
                                    st.error("Credenziali non valide.")
                                else:
                                    st.error(f"Errore server: {response.text}")
                            except requests.exceptions.ConnectionError:
                                st.error("Errore di connessione al servizio di autenticazione.")

            with tab2:
                st.write("")
                st.info("Registrazione nuovo personale medico.")
                new_u = st.text_input("Nuovo Username", key="r_u")
                new_p = st.text_input("Nuova Password", type="password", key="r_p")
                
                st.write("")
                if st.button("Completa Registrazione"):
                    if not new_u or not new_p:
                        st.warning("Tutti i campi sono obbligatori.")
                    else:
                        with st.spinner("Creazione utenza..."):
                            try:
                                res = requests.post(f"{AUTH_URL}/register", json={'username': new_u, 'password': new_p})
                                if res.status_code == 200: 
                                    st.success("✅ Utenza creata con successo. Procedere al login.")
                                elif res.status_code == 400:
                                    st.warning("Utente già esistente nel database.")
                                else: 
                                    st.error("Errore durante la registrazione.")
                            except: 
                                st.error("Servizio non raggiungibile.")

# --- FUNZIONE PRINCIPALE (DASHBOARD) ---
def main_app():
    # 1. Sidebar
    with st.sidebar:
        st.title("Area Clinica")
        st.write(f"Medico: **{st.session_state.username}**")
        st.markdown("---")
        
        st.subheader("Archivio")
        if st.button("📄 Scarica Report PDF", type="secondary"):
            with st.spinner("Generazione PDF in corso..."):
                try:
                    params = {'doctor_id': st.session_state.username}
                    report_res = requests.get(f"{REPORT_URL}/generate_report", params=params)
                    
                    if report_res.status_code == 200:
                        st.download_button(
                            label="📥 Download PDF",
                            data=report_res.content,
                            file_name=f"report_{st.session_state.username}.pdf",
                            mime="application/pdf"
                        )
                        st.success("Report generato.")
                    else:
                        st.error(f"Errore generazione: {report_res.text}")
                except Exception as e:
                    st.error("Servizio Report non raggiungibile.")

        st.markdown("---")
        if st.button("Esci"):
            st.session_state.auth_token = None
            st.rerun()

    headers = {'Authorization': f'Bearer {st.session_state.auth_token}'}

    # 2. TAB PRINCIPALI
    tab_analysis, tab_add = st.tabs(["📂 Cartelle Pazienti", "➕ Nuova Visita & Analisi AI"])

    # ---------------------------------------------------------
    # SCHEDA 1: CONSULTAZIONE (LEGGE STORICO E CF)
    # ---------------------------------------------------------
    with tab_analysis:
        st.subheader("📂 Archivio Pazienti e Dettaglio Visite")
        
        # 1. SCARICAMENTO DATI
        all_visits_data = []
        try:
            res = requests.get(f"{AUTH_URL}/patients", headers=headers)
            if res.status_code == 200:
                all_visits_data = res.json()
            else:
                st.error("Impossibile recuperare i dati.")
        except:
            st.warning("⚠️ Database non raggiungibile.")

        if all_visits_data:
            # 2. RAGGRUPPAMENTO PAZIENTI UNICI
            unique_patients_map = {}
            for visit in all_visits_data:
                cf = visit.get('fiscal_code', 'N/D')
                name = visit.get('full_name', 'Sconosciuto')
                if cf not in unique_patients_map:
                    unique_patients_map[cf] = name

            # 3. SELEZIONE PAZIENTE
            def format_func(cf_key):
                return f"{unique_patients_map[cf_key]} ({cf_key})"

            selected_cf = st.selectbox(
                "Seleziona Paziente:", 
                options=list(unique_patients_map.keys()),
                format_func=format_func,
                key="history_selectbox_full"
            )

            # 4. VISUALIZZAZIONE DETTAGLIATA
            if selected_cf:
                st.markdown("---")
                p_name = unique_patients_map[selected_cf]
                
                # Filtra le visite di questo paziente
                patient_history = [v for v in all_visits_data if v.get('fiscal_code') == selected_cf]
                # Ordina per data decrescente (dal più recente)
                patient_history.sort(key=lambda x: x.get('visit_date', ''), reverse=True)
                
                st.info(f"Paziente: **{p_name}** | Codice Fiscale: **{selected_cf}** | Visite trovate: **{len(patient_history)}**")

                # CICLO SU OGNI VISITA TROVATA
                for i, report in enumerate(patient_history):
                    # Formattazione Data e Titolo
                    raw_date = report.get('date', '')
                    nice_date = raw_date[:16].replace("T", " ") if raw_date else "Data N/D"
                    risk_label = "🔴 ALTO RISCHIO" if report.get('prediction') == 1 else "🟢 Basso Rischio"
                    report_id = report.get('id')

                    # Usiamo un expander per ogni visita per tenere ordinato, ma dentro mostriamo TUTTO
                    with st.expander(f"📄 Visita del {nice_date} — Esito: {risk_label}", expanded=(i==0)):
                        
                        st.markdown("#### 👤 Dati Anagrafici e Generali")
                        c_gen1, c_gen2, c_gen3, c_gen4 = st.columns(4)
                        with c_gen1:
                            st.text_input("Età", value=report.get('age'), disabled=True, key=f"v_{i}_age")
                        with c_gen2:
                            sex_str = "Maschio" if report.get('sex') == 1 else "Femmina"
                            st.text_input("Sesso", value=sex_str, disabled=True, key=f"v_{i}_sex")
                        with c_gen3:
                            st.text_input("Pressione (trtbps)", value=f"{report.get('trtbps')} mm Hg", disabled=True, key=f"v_{i}_bps")
                        with c_gen4:
                            st.text_input("Colesterolo", value=f"{report.get('chol')} mg/dl", disabled=True, key=f"v_{i}_chol")

                        st.markdown("#### Parametri Cardiaci Primari")
                        c_card1, c_card2, c_card3, c_card4 = st.columns(4)
                        with c_card1:
                            st.text_input("Dolore Toracico (CP)", value=f"Tipo {report.get('cp')}", disabled=True, key=f"v_{i}_cp")
                        with c_card2:
                            st.text_input("Freq. Max (thalachh)", value=report.get('thalachh'), disabled=True, key=f"v_{i}_thal")
                        with c_card3:
                            fbs_str = "> 120 mg/dl" if report.get('fbs') == 1 else "< 120 mg/dl"
                            st.text_input("Glicemia (fbs)", value=fbs_str, disabled=True, key=f"v_{i}_fbs")
                        with c_card4:
                            st.text_input("ECG a Riposo", value=f"Tipo {report.get('restecg')}", disabled=True, key=f"v_{i}_ecg")

                        st.markdown("#### 🔬 Parametri Avanzati")
                        c_adv1, c_adv2, c_adv3, c_adv4 = st.columns(4)
                        with c_adv1:
                            exng_str = "Sì" if report.get('exng') == 1 else "No"
                            st.text_input("Angina da sforzo (exng)", value=exng_str, disabled=True, key=f"v_{i}_exng")
                        with c_adv2:
                            st.text_input("Depressione ST (Oldpeak)", value=report.get('oldpeak'), disabled=True, key=f"v_{i}_old")
                        with c_adv3:
                            st.text_input("Pendenza ST (Slope)", value=f"Tipo {report.get('slp')}", disabled=True, key=f"v_{i}_slp")
                        with c_adv4:
                            st.text_input("Vasi Colorati (caa)", value=report.get('caa'), disabled=True, key=f"v_{i}_caa")
                        
                        # Ultimo parametro solitario
                        st.text_input("Thallium Stress Test", value=f"Risultato {report.get('thall')}", disabled=True, key=f"v_{i}_thall")

                        st.markdown("---")
                        # Pulsante di eliminazione
                        if st.button(f"🗑️ Elimina questo referto", key=f"del_btn_{report_id}"):
                             with st.spinner("Eliminazione..."):
                                try:
                                    del_res = requests.delete(f"{AUTH_URL}/patients/{report_id}", headers=headers)
                                    if del_res.status_code == 200:
                                        st.success("Eliminato!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Errore eliminazione")
                                except Exception as e:
                                    st.error(f"Errore: {e}")
        else:
            st.info("Nessun paziente in archivio.")
    # ---------------------------------------------------------
    # SCHEDA 2: NUOVA VISITA (FLUSSO: AI -> DB CON CF)
    # ---------------------------------------------------------
    with tab_add:
        st.subheader("Nuova Visita Medica")

        # --- FUNZIONE DI RESET ---
        def reset_form_data():
            # 1. Resetta i campi testo
            st.session_state.n_name = ""
            st.session_state.n_cf = ""
            
            # 2. Resetta i campi numerici/select eliminando la chiave dal session state.
            # In questo modo, al rerun, Streamlit userà il valore di default definito nel widget (value=...)
            keys_to_reset = [
                'n_age', 'n_sex', 'n_trtbps', 'n_chol', 'n_fbs', 'n_cp',
                'n_thal', 'n_exng', 'n_old', 'n_slp', 'n_caa', 'n_thall', 'n_restecg'
            ]
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]

        if st.session_state.get('trigger_reset', False):
            reset_form_data()
            st.session_state['trigger_reset'] = False

        # --- CALLBACK PER IL RADIO BUTTON ---
        def on_mode_change():
            # Se passo a "Nuovo Paziente", pulisco tutto
            if st.session_state.p_mode_sel == "Nuovo Paziente":
                st.session_state['trigger_reset'] = True

        # --- INIZIALIZZAZIONE VARIABILI SESSION STATE ---
        # Se le chiavi non esistono ancora, le creiamo vuote per evitare errori
        if 'n_name' not in st.session_state: st.session_state.n_name = ""
        if 'n_cf' not in st.session_state: st.session_state.n_cf = ""
        
        st.write("📅 **Data e Ora della Visita**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            d_date = st.date_input("Data", value="today", key="new_date_inp")
        with col_d2:
            d_time = st.time_input("Ora", value="now", key="new_time_inp")
        
        visit_datetime_str = f"{d_date} {d_time}"

        st.markdown("---")

        patient_mode = st.radio("Tipologia Inserimento:", ["Paziente Già Registrato", "Nuovo Paziente"], horizontal=True, key="p_mode_sel", on_change=on_mode_change)

        # --- LOGICA GESTIONE PAZIENTE ---
        is_locked = False
        
        if patient_mode == "Paziente Già Registrato":
            is_locked = True # Blocchiamo i campi per evitare errori di battitura su pazienti esistenti
            unique_patients = {}
            try:
                res = requests.get(f"{AUTH_URL}/patients", headers=headers)
                if res.status_code == 200:
                    for p in res.json():
                        cf_key = p.get('fiscal_code', 'N/D')
                        if cf_key not in unique_patients:
                            unique_patients[cf_key] = p['full_name']
                else:
                    st.error("Errore caricamento lista pazienti.")
            except:
                st.warning("DB Offline")

            options = [f"{name} ({cf})" for cf, name in unique_patients.items()]
            # Selectbox per scegliere il paziente
            selected_p = st.selectbox("Seleziona Paziente:", options, key="sel_exist_p")
            
            if selected_p:
                extracted_name = selected_p.split(" (")[0]
                extracted_cf = selected_p.split(" (")[1].replace(")", "")
                
                # --- PUNTO CRUCIALE: AGGIORNIAMO IL SESSION STATE ---
                # Questo aggiornerà automaticamente i campi di input sottostanti
                st.session_state.n_name = extracted_name
                st.session_state.n_cf = extracted_cf
                
                st.success(f"Paziente selezionato: **{extracted_name}**")
        
        else:
            # Se siamo su "Nuovo Paziente", sblocchiamo i campi.
            # Nota: Non cancelliamo il session state qui per non cancellare quello che l'utente sta scrivendo.
            is_locked = False

        st.markdown("---")

        with st.form("new_patient_form_v6"):
            st.write("👤 **Anagrafica Paziente**")
            
            if is_locked:
                st.caption("🔒 *I dati anagrafici sono precompilati e bloccati.*")

            c_ana_1, c_ana_2 = st.columns(2)
            with c_ana_1:
                new_name = st.text_input(
                    "Nome e Cognome", 
                    key="n_name",       # <--- Streamlit leggerà st.session_state.n_name
                    disabled=is_locked 
                )
            with c_ana_2:
                new_cf = st.text_input(
                    "Codice Fiscale", 
                    key="n_cf",         # <--- Streamlit leggerà st.session_state.n_cf
                    disabled=is_locked 
                ).upper()

            st.write("🩺 **Parametri Clinici**")
            c1, c2 = st.columns(2)
            with c1:
                n_age = st.number_input("Età", 18, 100, 50, key="n_age")
                n_sex_label = st.radio("Sesso", ["Maschio", "Femmina"], horizontal=True, key="n_sex")
                n_sex = 1 if n_sex_label == "Maschio" else 0
                n_trtbps = st.number_input("Pressione a Riposo (mm Hg)", 90, 200, 120, key="n_trtbps")
                n_chol = st.number_input("Colesterolo (mg/dl)", 100, 600, 200, key="n_chol")
                n_fbs_label = st.radio("Glicemia > 120 mg/dl?", ["No", "Sì"], horizontal=True, key="n_fbs")
                n_fbs = 1 if n_fbs_label == "Sì" else 0
                n_cp = st.selectbox("Tipo Dolore Toracico (CP)", (0,1,2,3), key="n_cp")

            with c2:
                n_thalachh = st.number_input("Frequenza Cardiaca Max", 70, 220, 150, key="n_thal")
                n_exng_label = st.radio("Angina da Esercizio?", ["No", "Sì"], horizontal=True, key="n_exng")
                n_exng = 1 if n_exng_label == "Sì" else 0
                n_oldpeak = st.number_input("Depressione ST (Oldpeak)", 0.0, 6.0, 1.0, key="n_old")
                n_slp = st.selectbox("Slope ST", (0,1,2), key="n_slp")
                n_caa = st.selectbox("Numero Vasi (CAA)", (0,1,2,3,4), key="n_caa")
                n_thall = st.selectbox("Thallium Test", (0,1,2,3), key="n_thall")
                n_restecg = st.selectbox("ECG a Riposo", (0,1,2), key="n_restecg")

            st.write("")
            privacy_consent = st.checkbox("Confermo di aver acquisito il consenso al trattamento dati dal paziente.")
            submitted = st.form_submit_button("💾 Salva Visita", type="primary")
            
            if submitted:
                if not privacy_consent:
                     st.error("⚠️ È obbligatorio confermare il consenso privacy per procedere.")
                elif not new_name or not new_cf:
                    st.warning("⚠️ Nome e Codice Fiscale sono obbligatori.")
                else:
                    prediction_val = None
                    ai_success = False
                    ai_message = ""

                    with st.spinner("Analisi clinica AI in corso..."):
                        input_ai = { 
                            "features": [n_age, n_sex, n_cp, n_trtbps, n_chol, n_fbs, n_restecg, 
                                         n_thalachh, n_exng, n_oldpeak, n_slp, n_caa, n_thall] 
                        }
                        try:
                            ml_res = requests.post(f"{BACKEND_URL}/predict", json=input_ai, headers=headers)
                            if ml_res.status_code == 200:
                                res_json = ml_res.json()
                                prediction_val = res_json['prediction'] 
                                ai_message = res_json['message']
                                ai_success = True
                            else:
                                st.error(f"Errore AI: {ml_res.text}")
                        except:
                            st.error("Servizio AI non raggiungibile")

                    if ai_success:
                        with st.spinner("Salvataggio nel DB..."):
                            payload_db = {
                                "full_name": new_name,
                                "fiscal_code": new_cf,
                                "age": n_age, "sex": n_sex, "cp": n_cp, "trtbps": n_trtbps, 
                                "chol": n_chol, "fbs": n_fbs, "restecg": n_restecg, 
                                "thalachh": n_thalachh, "exng": n_exng, "oldpeak": n_oldpeak, 
                                "slp": n_slp, "caa": n_caa, "thall": n_thall,
                                "prediction": prediction_val,
                                "visit_date": visit_datetime_str 
                            }
                            
                            try:
                                save_res = requests.post(f"{AUTH_URL}/patients", json=payload_db, headers=headers)
                                if save_res.status_code == 200:
                                    st.toast("Visita salvata correttamente!", icon="✅") 
                                    if prediction_val == 1:
                                        st.error(f"⚠️ RISCHIO ALTO: {ai_message}")
                                    else:
                                        st.success(f"✅ RISCHIO BASSO: {ai_message}")
                                    st.info(f"Visita del **{visit_datetime_str}** registrata per {new_name}.")
                                    st.session_state['trigger_reset'] = True
                                    time.sleep(2) 
                                    st.rerun() 
                                else:
                                    st.error(f"Errore DB: {save_res.text}")
                            except Exception as e:
                                st.error(f"Errore connessione: {e}")

# MAIN LOOP
if st.session_state.auth_token is None:
    login_page()
else:
    main_app()