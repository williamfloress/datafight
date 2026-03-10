# DATAFIGHT Frontend

Interfaz con un botón que ejecuta el pipeline completo (scraper + predictor) en memoria y muestra las predicciones.

## Cómo usar

```bash
cd V1
pip install -r requirements.txt
python server.py
```

Abrir **http://localhost:5000/**

## Botón "Analizar próximo evento"

- Ejecuta scraper (ufcstats.com) + predictor en memoria
- No genera archivos; datos en memoria y localStorage
- **Rate limit:** 1 análisis cada 30 min (protección del sitio)

## Contenido

- **index.html** — Estructura semántica, cabecera con evento, grid de peleas
- **styles.css** — Tema oscuro, tarjetas por pelea, resaltado del favorito
- **app.js** — Fetch de predicciones, renderizado dinámico, escape XSS

## Diseño

- El peleador con mayor probabilidad se resalta con borde, color y badge "Favorito"
- Barra de probabilidad comparativa debajo de cada pelea
- Enlaces a perfiles en ufcstats.com
- Responsive (mobile-first)
