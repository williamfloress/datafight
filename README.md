# DATAFIGHT V1

Implementación del **MVP v1** del proyecto DATAFIGHT: Motor de Analytics de MMA. Esta carpeta contiene el pipeline de datos y la base para la primera iteración del sistema.

---

## ¿Qué es DATAFIGHT V1?

**DATAFIGHT** es un sistema automatizado que predice resultados de combates de MMA basándose en el **"choque de estilos"** entre peleadores, en lugar de rankings de popularidad o récords simples.

El **V1 (MVP)** prioriza la validación del modelo de extracción y análisis de datos. La arquitectura es estática por diseño para iterar rápido:

| Componente | Tecnología |
|------------|------------|
| **Motor de Datos** | Scripts de web scraping en Python |
| **Almacenamiento** | Archivos estáticos `.json` |
| **Frontend** | Página web estática (HTML/CSS/Vanilla JS) consumiendo el JSON |

---

## Pipeline del MVP v1

El proyecto se organiza en 4 fases:

```
Fase 1 (Scraping) ──► Fase 2 (Feature Engineering) ──► Fase 3 (Modelo + JSON) ──► Fase 4 (Frontend)
```

---

## Contenido de esta carpeta

### Scraper UFC Stats (Fase 1)

Script en Python que extrae del evento UFC más próximo:

1. **Evento:** nombre, fecha, URL de detalles
2. **Peleas:** parejas de peleadores con categoría de peso (`weight_class`)
3. **Estadísticas por peleador:**
   - *Striking:* SLpM, precisión, SApM, defensa
   - *Grappling:* promedio de derribos, precisión, defensa, sumisiones
   - *Básicos:* record (W-L-D), stance, DOB

**Fuente:** [ufcstats.com](http://ufcstats.com/statistics/events/upcoming)

**Salida:** `scraper/evento_proximo.json` — datos crudos listos para el predictor.

### Predictor (Fase 2–3)

Script que calcula probabilidades de victoria por pelea usando la lógica de `documentation/logica_probabilistica.md`:

1. **Net Striking:** SLpM - SApM
2. **Grappling:** TD_Avg × (1 - TD_Def del oponente)
3. **Edad:** Si diferencia ≥ 5 años, el más joven recibe ~70%

**Entrada:** `scraper/evento_proximo.json`  
**Salida:** `output/predicciones.json`

```bash
cd V1/predictor
python predictor.py
```

---

## Requisitos

- Python 3.10+
- Playwright

## Instalación

```bash
cd V1/scraper
pip install -r requirements.txt
playwright install chromium
```

## Uso

**1. Extraer datos del evento próximo:**
```bash
cd V1/scraper
python scraper_ufc.py
```

**2. Calcular predicciones:**
```bash
cd V1/predictor
python predictor.py
```

**3. Iniciar el servidor:**
```bash
cd V1
pip install -r requirements.txt
python server.py
```
Abrir http://localhost:5000/

**Un solo botón:** "Analizar próximo evento" ejecuta scraper + predictor en memoria (sin archivos). Rate limit: 1 análisis cada 30 min para proteger ufcstats.com.

## Estructura del JSON generado

```json
{
  "evento": {
    "nombre": "UFC Fight Night: Emmett vs. Vallejos",
    "fecha": "March 14, 2026",
    "url_detalles": "http://ufcstats.com/event-details/..."
  },
  "peleas": [
    {
      "peleador_1": {
        "nombre": "Josh Emmett",
        "perfil": "http://ufcstats.com/fighter-details/...",
        "estadisticas": {
          "record": "19-6-0",
          "striking": { "slpm": 3.72, "str_acc": 0.35, "sapm": 4.43, "str_def": 0.6 },
          "grappling": { "td_avg": 1.08, "td_acc": 0.37, "td_def": 0.43, "sub_avg": 0.1 }
        }
      },
      "peleador_2": { ... },
      "weight_class": "Featherweight"
    }
  ],
  "extraido_en": "2026-03-09T..."
}
```

### Estructura de predicciones.json

```json
{
  "evento": { "nombre": "...", "fecha": "...", "url_detalles": "..." },
  "peleas": [
    {
      "peleador_1": {
        "nombre": "...",
        "perfil": "...",
        "probabilidad_victoria": 0.21,
        "record": "19-6-0"
      },
      "peleador_2": { ... },
      "weight_class": "Featherweight",
      "ganador_predicho": "Kevin Vallejos",
      "detalle_modelo": {
        "net_striking": { "peleador_1": -0.71, "peleador_2": 1.07 },
        "grappling_efectividad": { "peleador_1_vs_2": 0.18, "peleador_2_vs_1": 0.4 },
        "edad": { "peleador_1": 41, "peleador_2": 25 }
      }
    }
  ],
  "generado_en": "2026-03-09T..."
}
```

