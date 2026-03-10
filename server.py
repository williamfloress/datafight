"""
DATAFIGHT - Servidor backend. Pipeline en memoria: scraper + predictor sin archivos.
Rate limit en "Analizar próximo evento" para no sobrecargar ufcstats.com.
"""
import os
import sys
import time

from flask import Flask, jsonify, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
SCRAPER_DIR = os.path.join(BASE_DIR, "scraper")

# Rate limit: mínimo minutos entre ejecuciones del scraper
RATE_LIMIT_MINUTES = 30

# Estado en memoria (sin archivos)
_ultima_prediccion = None
_ultimo_scrape_at = None

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


def _run_pipeline():
    """Ejecuta scraper + predictor en memoria. Retorna (ok, data|error_msg)."""
    global _ultima_prediccion, _ultimo_scrape_at

    sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, SCRAPER_DIR)
    try:
        import scraper_ufc
        from predictor.predictor import procesar_evento
    finally:
        if SCRAPER_DIR in sys.path:
            sys.path.remove(SCRAPER_DIR)
        if BASE_DIR in sys.path:
            sys.path.remove(BASE_DIR)

    data_scraper = scraper_ufc.ejecutar_scraper()
    if not data_scraper:
        return False, "El scraper no encontró eventos o falló."

    predicciones = procesar_evento(data_scraper)
    _ultima_prediccion = predicciones
    _ultimo_scrape_at = time.time()
    return True, predicciones


def _rate_limit_ok() -> tuple[bool, float | None]:
    """Retorna (ok, segundos_restantes). Si ok=True, segundos_restantes es None."""
    global _ultimo_scrape_at
    if _ultimo_scrape_at is None:
        return True, None
    elapsed = time.time() - _ultimo_scrape_at
    required = RATE_LIMIT_MINUTES * 60
    if elapsed < required:
        return False, required - elapsed
    return True, None


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.post("/api/actualizar")
def actualizar():
    """
    Analiza el próximo evento: ejecuta scraper + predictor en memoria.
    Rate limit: 1 ejecución cada RATE_LIMIT_MINUTES minutos.
    """
    ok_limit, segundos_restantes = _rate_limit_ok()
    if not ok_limit:
        mins = int(segundos_restantes // 60)
        return (
            jsonify({
                "ok": False,
                "error": "rate_limit",
                "message": f"Debes esperar {mins} minutos antes de analizar de nuevo (protección del sitio).",
                "segundos_restantes": int(segundos_restantes),
            }),
            429,
        )

    ok, result = _run_pipeline()
    if ok:
        return jsonify({"ok": True, "predicciones": result})
    return jsonify({"ok": False, "error": result}), 500


@app.get("/api/predicciones")
def get_predicciones():
    """Devuelve la última predicción en memoria (si existe)."""
    global _ultima_prediccion
    if _ultima_prediccion is None:
        return jsonify({"evento": None, "peleas": []})
    return jsonify(_ultima_prediccion)


@app.post("/api/limpiar")
def limpiar_predicciones():
    """Limpia la caché de predicciones en el servidor."""
    global _ultima_prediccion
    _ultima_prediccion = None
    return jsonify({"ok": True})


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
