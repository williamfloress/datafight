# Predictor DATAFIGHT V1

Calcula probabilidades de victoria para cada pelea del evento próximo usando la lógica definida en `documentation/logica_probabilistica.md`.

## Requisitos

- Python 3.10+
- Archivo `../scraper/evento_proximo.json` (generado por el scraper)

## Uso

```bash
cd V1/predictor
python predictor.py
```

## Entrada

Lee `V1/scraper/evento_proximo.json` (salida del scraper).

## Salida

Genera `V1/output/predicciones.json` con:

- **evento:** nombre, fecha, url_detalles
- **peleas:** por cada pelea:
  - `peleador_1` / `peleador_2`: nombre, perfil, `probabilidad_victoria` (0–1), record
  - `weight_class`
  - `ganador_predicho`
  - `detalle_modelo`: net_striking, grappling_efectividad, edad, ventaja_cruda

## Lógica del modelo

1. **Net Striking:** `SLpM - SApM` — diferencial de intercambios de pie
2. **Grappling:** `TD_Avg_A × (1 - TD_Def_B)` — efectividad de derribos vs defensa del oponente
3. **Edad:** Si diferencia ≥ 5 años, el más joven recibe ~70% de probabilidad

Los factores se combinan en una ventaja y se convierten a probabilidad con una función sigmoide (tanh).
