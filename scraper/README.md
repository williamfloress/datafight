# Scraper UFC Stats

Extrae el evento UFC más próximo, las peleas (parejas + categoría de peso) y las estadísticas de cada peleador desde [ufcstats.com](http://ufcstats.com/statistics/events/upcoming).

## Requisitos

- Python 3.10+
- Playwright

## Instalación

```bash
pip install -r requirements.txt
playwright install chromium
```

## Uso

```bash
python scraper_ufc.py
```

## Salida

Genera `evento_proximo.json` en esta carpeta.
