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
* **Security Testing:** Docker Scout, Gitleaks, Semgrep, OWASP ZAP (wrk for Load Testing)

## 🚀 Deployment
*(Note: Ensure you have a running Kubernetes cluster and `kubectl` configured).*
1. Clone the repository:
   ```bash
   git clone https://github.com/YourUsername/Heart-Attack-Prediction-DevSecOps.git
2. Apply the Kubernetes manifests (Deployments, Services, HPA, Secrets):
   ```bash
   kubectl apply -f k8s/
3. Access the Streamlit frontend via the Nginx Ingress Controller IP.

Project developed for the Secure Cloud Computing course, A.Y. 2025/2026.
