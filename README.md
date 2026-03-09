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

**Salida:** `scraper/evento_proximo.json` — datos crudos listos para Fase 2 (Feature Engineering).

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

```bash
cd V1/scraper
python scraper_ufc.py
```

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

