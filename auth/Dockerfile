FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .

# Prima del vulnerability scan con Docker Scout
# RUN pip install --no-cache-dir -r requirements.txt

# Prima aggiorniamo pip all'ultima versione, poi installiamo le librerie
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
    
COPY . .
EXPOSE 5001
CMD ["python", "app.py"]