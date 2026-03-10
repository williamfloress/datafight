# Imagen oficial de Playwright con Python y Chromium preinstalado
# La versión debe coincidir con playwright en requirements.txt
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY server.py .
COPY frontend/ frontend/
COPY predictor/ predictor/
COPY scraper/ scraper/

# Puerto por defecto (Railway inyecta PORT)
ENV PORT=5000
EXPOSE 5000

# Usar shell para expandir $PORT en runtime
# timeout=600 (10 min): el scraping puede tardar 2-5 min según el frontend
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --timeout 600 server:app"]
