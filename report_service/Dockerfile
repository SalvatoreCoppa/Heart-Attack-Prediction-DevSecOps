FROM python:3.9-slim

WORKDIR /app

# Installazione delle dipendenze
COPY requirements.txt .

# Prima del vulnerability scan con Docker Scout
# RUN pip install --no-cache-dir -r requirements.txt

# Prima aggiorniamo pip all'ultima versione, poi installiamo le librerie
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
    
# Copia dello script
COPY report.py .

# Creazione della cartella per l'output
RUN mkdir /output

# Comando di default
CMD ["python", "report.py"]