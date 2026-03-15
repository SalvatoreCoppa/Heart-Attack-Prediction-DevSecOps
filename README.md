# Secure Cloud AI: Heart Attack Prediction App 🫀☁️

![Architecture](https://img.shields.io/badge/Architecture-Kubernetes-326CE5)
![Backend](https://img.shields.io/badge/Backend-Python%20%7C%20Flask-3776AB)
![Security](https://img.shields.io/badge/Security-DevSecOps-red)
![Database](https://img.shields.io/badge/Database-PostgreSQL-336791)

## 📌 Overview
This repository contains the architecture and microservices for a secure, cloud-native **Clinical Decision Support System (SaaS)**. 
Designed for the healthcare sector, the application evaluates 13 physiological and cardiovascular risk factors using an offline-trained AI model to predict heart attack risks in real-time.

The infrastructure was built with a strong focus on **High Availability** and **Data Privacy (GDPR compliance)**, strictly adhering to the Cloud Security Alliance (CSA CCM) guidelines.

## 🛡️ Architecture & Security Highlights
* **Kubernetes Orchestration:** Containerized microservices (Flask backend, Streamlit frontend) managed via K8s with proactive **Horizontal Pod Autoscaling (HPA)** for fault tolerance and traffic spike management.
* **Data Privacy & Encryption:** * Master-Slave PostgreSQL architecture for high availability.
  * Sensitive PII protected via **Encryption at Rest** (`pgcrypto`).
  * Cryptographic keys managed via Kubernetes Secrets and mounted strictly in volatile RAM (`tmpfs`), never written to disk.
* **DevSecOps Pipeline:** A "Shift-Left" security approach validated through:
  * **Docker Scout:** Container CVE remediation.
  * **Gitleaks:** Prevention of Secret Sprawl.
  * **Semgrep:** SAST source code analysis.
  * **OWASP ZAP:** Dynamic DAST scanning.
* **Perimeter Defense:** Nginx Reverse Proxy hardened against volumetric DoS attacks, enforcing strict HTTP Security Headers to prevent Clickjacking and MIME-sniffing.

## 🛠️ Tech Stack
* **Cloud & DevOps:** Kubernetes, Docker, Nginx Reverse Proxy
* **Software:** Python, Flask (API), Streamlit (Frontend), Scikit-Learn (AI Model)
* **Database:** PostgreSQL (Master-Slave, pgcrypto)
* **Security Testing:** Docker Scout, Gitleaks, Semgrep, OWASP ZAP

## 🚀 How to Run and Deploy

The AI model is pre-trained and directly integrated into the system. You can spin up the entire infrastructure using either Docker Compose or a local Kubernetes cluster (KIND).

### Option 1: Local Environment (Docker Compose)
The fastest way to test the microservices (`auth`, `backend`, `frontend`, `report_service`) locally:

1. Clone the repository and navigate into it:
   ```bash
   git clone https://github.com/YourUsername/Heart-Attack-Prediction-DevSecOps.git
   cd Heart-Attack-Prediction-DevSecOps
   ```
2. Build and start the infrastructure:
   ```bash
   docker-compose up --build
   ```

### Option 2: Local Kubernetes Cluster (KIND)
To test the Kubernetes orchestration, High Availability, and HPA logic locally:

1. Create the local cluster using the provided configuration:
   ```bash
   ./kind.exe create cluster --config kind-config.yaml
   ```
2. Deploy the Metrics Server (required for HPA to work):
   ```bash
   kubectl apply -f metrics-server.yaml
   ```
3. Apply the application manifests, HPA, and Role Bindings:
   ```bash
   kubectl apply -f k8s-deploy.yaml
   kubectl apply -f hpa.yaml
   kubectl apply -f cluster_rolebinding.yaml
   kubectl apply -f dashboard-adminuser.yaml
   ```
