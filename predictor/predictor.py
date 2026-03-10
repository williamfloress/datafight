"""
Predictor DATAFIGHT V1: calcula probabilidades de victoria por pelea.

Implementa la lógica de documentation/logica_probabilistica.md:
1. Net Striking = SLpM - SApM (diferencial de intercambios)
2. Efectividad Grappling = TD_Avg_A × (1 - TD_Def_B) (amenaza de derribo)
3. Diferencia de edad: si ≥5 años, el más joven gana ~70% de las veces

Lee evento_proximo.json (salida del scraper) y genera predicciones.json.
"""
import json
import math
import os
import re
from datetime import datetime
from typing import Any

# Rutas por defecto
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
V1_DIR = os.path.dirname(SCRIPT_DIR)
INPUT_JSON = os.path.join(V1_DIR, "scraper", "evento_proximo.json")
OUTPUT_JSON = os.path.join(V1_DIR, "output", "predicciones.json")


def _safe_float(val: Any) -> float:
    """Convierte a float; retorna 0.0 si es None o inválido."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _parse_dob_to_age(dob: str | None) -> int | None:
    """
    Parsea DOB (ej. 'Mar 04, 1985', 'Dec 08, 2001') y retorna edad en años.
    Retorna None si no se puede parsear.
    """
    if not dob or not isinstance(dob, str) or not dob.strip():
        return None
    match = re.search(r"(\d{4})", dob.strip())
    if not match:
        return None
    try:
        year = int(match.group(1))
        return datetime.now().year - year
    except ValueError:
        return None


def _net_striking(slpm: float, sapm: float) -> float:
    """Net Striking = SLpM - SApM (documentation/logica_probabilistica.md §1)."""
    return slpm - sapm


def _grappling_efectividad_vs(td_avg: float, td_def_oponente: float) -> float:
    """
    Efectividad esperada de A vs B: TD_Avg_A × (1 - TD_Def_B).
    (documentation/logica_probabilistica.md §2)
    """
    return td_avg * (1.0 - td_def_oponente)


def _calcular_probabilidades(
    p1: dict,
    p2: dict,
) -> tuple[float, float, dict]:
    """
    Calcula probabilidad de victoria para peleador_1 y peleador_2.

    Retorna (prob_p1, prob_p2, detalle) donde detalle incluye los factores usados.
    """
    s1 = p1.get("estadisticas") or {}
    s2 = p2.get("estadisticas") or {}

    str1 = s1.get("striking") or {}
    str2 = s2.get("striking") or {}
    gr1 = s1.get("grappling") or {}
    gr2 = s2.get("grappling") or {}

    # 1. Net Striking
    slpm1 = _safe_float(str1.get("slpm"))
    sapm1 = _safe_float(str1.get("sapm"))
    slpm2 = _safe_float(str2.get("slpm"))
    sapm2 = _safe_float(str2.get("sapm"))

    net1 = _net_striking(slpm1, sapm1)
    net2 = _net_striking(slpm2, sapm2)
    net_diff = net1 - net2  # positivo = ventaja p1

    # 2. Grappling: efectividad de cada uno contra la defensa del otro
    td_avg1 = _safe_float(gr1.get("td_avg"))
    td_def1 = _safe_float(gr1.get("td_def"))
    td_avg2 = _safe_float(gr2.get("td_avg"))
    td_def2 = _safe_float(gr2.get("td_def"))

    eff1_vs_2 = _grappling_efectividad_vs(td_avg1, td_def2)
    eff2_vs_1 = _grappling_efectividad_vs(td_avg2, td_def1)
    gr_diff = eff1_vs_2 - eff2_vs_1  # positivo = ventaja p1

    # 3. Edad: si diferencia ≥ 5 años, el más joven gana ~70%
    age1 = _parse_dob_to_age(s1.get("dob"))
    age2 = _parse_dob_to_age(s2.get("dob"))
    age_factor = 0.0  # ventaja para p1: positivo = p1 más joven
    if age1 is not None and age2 is not None:
        diff = age2 - age1  # positivo si p2 es mayor (p1 más joven)
        if abs(diff) >= 5:
            age_factor = 0.4 if diff > 0 else -0.4  # +0.4 → prob ~70% para el más joven

    # Combinar factores en ventaja para peleador_1
    # Pesos: striking y grappling en escala similar; edad tiene impacto fuerte (~70%)
    w_striking = 0.12
    w_grappling = 0.20
    ventaja_p1 = (
        w_striking * net_diff
        + w_grappling * gr_diff
        + age_factor
    )

    # Convertir ventaja a probabilidad: sigmoide suave
    # prob_p1 = 0.5 + 0.5 * tanh(ventaja) → [0, 1]
    prob_p1 = 0.5 + 0.5 * math.tanh(ventaja_p1)
    prob_p2 = 1.0 - prob_p1

    # Redondear a 2 decimales
    prob_p1 = round(prob_p1, 2)
    prob_p2 = round(prob_p2, 2)

    # Ajuste por si hay desborde por redondeo
    if prob_p1 + prob_p2 != 1.0:
        prob_p1 = round(1.0 - prob_p2, 2)

    detalle = {
        "net_striking": {"peleador_1": round(net1, 2), "peleador_2": round(net2, 2)},
        "grappling_efectividad": {
            "peleador_1_vs_2": round(eff1_vs_2, 2),
            "peleador_2_vs_1": round(eff2_vs_1, 2),
        },
        "edad": {"peleador_1": age1, "peleador_2": age2},
        "ventaja_cruda": round(ventaja_p1, 4),
    }

    return prob_p1, prob_p2, detalle


def procesar_evento(data: dict) -> dict:
    """
    Procesa el JSON del scraper y añade probabilidades a cada pelea.
    """
    evento = data.get("evento", {})
    peleas = data.get("peleas", [])

    peleas_con_prediccion = []
    for pelea in peleas:
        p1 = pelea.get("peleador_1", {})
        p2 = pelea.get("peleador_2", {})

        prob1, prob2, detalle = _calcular_probabilidades(p1, p2)

        ganador = p1["nombre"] if prob1 >= prob2 else p2["nombre"]

        s1 = p1.get("estadisticas") or {}
        s2 = p2.get("estadisticas") or {}

        age1 = detalle.get("edad", {}).get("peleador_1")
        age2 = detalle.get("edad", {}).get("peleador_2")

        peleas_con_prediccion.append({
            "peleador_1": {
                "nombre": p1.get("nombre", ""),
                "perfil": p1.get("perfil", ""),
                "probabilidad_victoria": prob1,
                "record": s1.get("record", ""),
                "edad": age1,
                "ultimas_peleas": s1.get("ultimas_peleas", []),
                "estadisticas": {
                    "striking": s1.get("striking", {}),
                    "grappling": s1.get("grappling", {}),
                    "stance": s1.get("stance", ""),
                    "dob": s1.get("dob", ""),
                    "height": s1.get("height", ""),
                    "reach": s1.get("reach", ""),
                    "weight": s1.get("weight", ""),
                },
            },
            "peleador_2": {
                "nombre": p2.get("nombre", ""),
                "perfil": p2.get("perfil", ""),
                "probabilidad_victoria": prob2,
                "record": s2.get("record", ""),
                "edad": age2,
                "ultimas_peleas": s2.get("ultimas_peleas", []),
                "estadisticas": {
                    "striking": s2.get("striking", {}),
                    "grappling": s2.get("grappling", {}),
                    "stance": s2.get("stance", ""),
                    "dob": s2.get("dob", ""),
                    "height": s2.get("height", ""),
                    "reach": s2.get("reach", ""),
                    "weight": s2.get("weight", ""),
                },
            },
            "weight_class": pelea.get("weight_class", ""),
            "ganador_predicho": ganador,
            "detalle_modelo": detalle,
        })

    return {
        "evento": evento,
        "peleas": peleas_con_prediccion,
        "generado_en": datetime.now().isoformat(),
    }


def main() -> None:
    print("Predictor DATAFIGHT V1 - Cálculo de probabilidades")
    print("-" * 50)

    if not os.path.exists(INPUT_JSON):
        print(f"Error: No se encontró {INPUT_JSON}")
        print("Ejecuta primero el scraper: python scraper_ufc.py")
        return

    with open(INPUT_JSON, encoding="utf-8") as f:
        data = json.load(f)

    resultado = procesar_evento(data)

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"Guardado: {OUTPUT_JSON}")
    print(f"\nEvento: {resultado['evento'].get('nombre', '')}")
    print(f"Fecha:  {resultado['evento'].get('fecha', '')}")
    print("\nPredicciones:")
    for pelea in resultado["peleas"]:
        p1 = pelea["peleador_1"]
        p2 = pelea["peleador_2"]
        print(f"  - {p1['nombre']} ({p1['probabilidad_victoria']*100:.0f}%) vs "
              f"{p2['nombre']} ({p2['probabilidad_victoria']*100:.0f}%) -> {pelea['ganador_predicho']}")

    print("\nListo.")


if __name__ == "__main__":
    main()
