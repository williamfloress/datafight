"""
Scraper UFC Stats V1: extrae evento, peleas (parejas + weight_class) y estadísticas de cada peleador.
Usa Playwright para navegar ufcstats.com.
Exporta únicamente JSON.
"""
from playwright.sync_api import sync_playwright
import json
import os
import re
import time
from datetime import datetime

BASE_URL = "http://ufcstats.com/statistics/events/upcoming"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON = "evento_proximo.json"
REQUEST_DELAY = 1.5  # segundos entre requests para no sobrecargar el servidor


def extraer_evento_proximo(page) -> dict | None:
    """Obtiene el primer evento de la lista (el más próximo) desde la tabla de eventos."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
    page.wait_for_load_state("domcontentloaded")

    # Tabla: table.b-statistics.table-events, primer enlace event-details
    link = page.locator('a[href*="event-details"]').first
    if not link.count():
        return None

    href = link.get_attribute("href")
    nombre_evento = link.inner_text().strip()

    # Fecha: span.b-statistics_date en la misma fila (si existe)
    fecha_str = ""
    row = link.locator("xpath=ancestor::tr")
    if row.count():
        date_span = row.locator("span.b-statistics_date")
        if date_span.count():
            fecha_str = date_span.first.inner_text().strip()
        else:
            # Fallback: celda siguiente con formato de fecha
            cells = row.locator("td")
            for i in range(cells.count()):
                text = cells.nth(i).inner_text().strip()
                if re.match(r"[A-Za-z]+\s+\d{1,2},\s+\d{4}", text):
                    fecha_str = text
                    break

    return {
        "nombre": nombre_evento,
        "fecha": fecha_str,
        "url_detalles": href,
    }


def extraer_peleas(page, url_evento: str) -> tuple[list[dict], str]:
    """
    Navega a la página del evento y extrae las peleas como parejas (fighter1, fighter2, weight_class).
    Tabla: table.b-fight-details_table, filas tr.js-fight-details-click
    """
    page.goto(url_evento, wait_until="networkidle", timeout=15000)
    page.wait_for_load_state("domcontentloaded")

    # Fecha: "Date: March 14, 2026" en el body
    fecha_str = ""
    page_text = page.inner_text("body")
    fecha_match = re.search(r"Date:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", page_text, re.I)
    if fecha_match:
        fecha_str = fecha_match.group(1).strip()
    else:
        fecha_match = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})", page_text)
        if fecha_match:
            fecha_str = fecha_match.group(1).strip()

    peleas = []
    rows = page.locator("tr.js-fight-details-click")

    for i in range(rows.count()):
        row = rows.nth(i)
        fighter_links = row.locator('a[href*="fighter-details"]')

        if fighter_links.count() < 2:
            continue

        nombre1 = fighter_links.nth(0).inner_text().strip()
        perfil1 = fighter_links.nth(0).get_attribute("href") or ""
        nombre2 = fighter_links.nth(1).inner_text().strip()
        perfil2 = fighter_links.nth(1).get_attribute("href") or ""

        # Weight class: buscar en el texto de la fila (estructura: Fighter1, Fighter2, View Matchup, Weight)
        WEIGHT_CLASSES = (
            "Women's Strawweight", "Women's Bantamweight", "Women's Flyweight",
            "Light Heavyweight", "Featherweight", "Heavyweight", "Lightweight",
            "Welterweight", "Middleweight", "Flyweight", "Bantamweight",
        )
        row_text = row.inner_text()
        weight_class = next((wc for wc in WEIGHT_CLASSES if wc in row_text), "")

        peleas.append({
            "peleador_1": {"nombre": nombre1, "perfil": perfil1},
            "peleador_2": {"nombre": nombre2, "perfil": perfil2},
            "weight_class": weight_class or "Unknown",
        })

    return peleas, fecha_str


def _parse_stat_value(text: str) -> float | None:
    """Convierte '45%' -> 0.45, '3.72' -> 3.72."""
    if not text or not text.strip():
        return None
    text = text.strip()
    if "%" in text:
        try:
            return float(re.sub(r"[^\d.]", "", text)) / 100.0
        except ValueError:
            return None
    try:
        return float(re.sub(r"[^\d.]", "", text))
    except ValueError:
        return None


def extraer_perfil_peleador(page, url_perfil: str) -> dict | None:
    """
    Extrae estadísticas del peleador desde su página de perfil.
    Career Statistics: SLpM, Str. Acc., SApM, Str. Def., TD Avg., TD Acc., TD Def., Sub. Avg.
    """
    page.goto(url_perfil, wait_until="networkidle", timeout=15000)
    page.wait_for_load_state("domcontentloaded")

    # Nombre: h2 o span.b-content__title-highlight (estructura: "Josh Emmett" o "Josh Emmett Record: 19-6-0")
    nombre = ""
    for sel in ("span.b-content__title-highlight", "h2.b-content__title"):
        el = page.locator(sel).first
        if el.count():
            text = el.inner_text().strip()
            # Quitar "Record: X-X-X" si está incluido
            if "Record:" in text:
                text = re.sub(r"\s*Record:.*$", "", text, flags=re.I).strip()
            nombre = text
            break
    if not nombre:
        h2 = page.locator("h2").first
        if h2.count():
            nombre = re.sub(r"\s*Record:.*$", "", h2.inner_text(), flags=re.I).strip()

    # Record: span.b-content__title-record "RECORD: 19-6-0"
    record = ""
    record_el = page.locator("span.b-content__title-record").first
    if record_el.count():
        record = record_el.inner_text().replace("RECORD:", "").strip()
    if not record:
        m = re.search(r"Record:\s*(\d+-\d+-\d+)", page.inner_text("body"), re.I)
        record = m.group(1) if m else ""

    body_text = page.inner_text("body")

    # Atributos básicos (Height, Weight, Reach, Stance, DOB)
    # ufcstats.com muestra "HEIGHT:", "REACH:" en mayúsculas
    height = weight = reach = stance = dob = ""
    list_items = page.locator(
        "li.b-list__box-list-item, li.b-list_box-list-item, li.b-list_box-list-item_type_block"
    )
    for i in range(list_items.count()):
        text = list_items.nth(i).inner_text().strip()
        text_lower = text.lower()
        if text_lower.startswith("height:"):
            height = re.sub(r"^height:\s*", "", text, flags=re.I).strip()
        elif text_lower.startswith("weight:"):
            weight = re.sub(r"^weight:\s*", "", text, flags=re.I).strip()
        elif text_lower.startswith("reach:"):
            reach = re.sub(r"^reach:\s*", "", text, flags=re.I).strip()
        elif text_lower.startswith("stance:"):
            stance = re.sub(r"^stance:\s*", "", text, flags=re.I).strip()
        elif text_lower.startswith("dob:"):
            dob = re.sub(r"^dob:\s*", "", text, flags=re.I).strip()
    # Fallback desde body si los li no matchean
    if not height:
        m = re.search(r"height:\s*([^\n]+)", body_text, re.I)
        height = m.group(1).strip() if m else ""
    if not weight:
        m = re.search(r"weight:\s*([^\n]+)", body_text, re.I)
        weight = m.group(1).strip() if m else ""
    if not reach:
        m = re.search(r"reach:\s*([^\n]+)", body_text, re.I)
        reach = m.group(1).strip() if m else ""
    if not stance:
        m = re.search(r"stance:\s*([^\n]+)", body_text, re.I)
        stance = m.group(1).strip() if m else ""
    if not dob:
        m = re.search(r"dob:\s*([^\n]+)", body_text, re.I)
        dob = m.group(1).strip() if m else ""

    # Career Statistics: parsear desde li.b-list_box-list-item_type_block o desde body como fallback
    slpm = sapm = str_acc = str_def = None
    td_avg = td_acc = td_def = sub_avg = None

    def _extract(m):
        return m.group(1) if m else None

    # Intentar primero con items específicos (estructura: cada li tiene 2 stats)
    stat_items = page.locator("li.b-list_box-list-item_type_block")
    for i in range(stat_items.count()):
        item_text = stat_items.nth(i).inner_text()
        if "SLpM:" in item_text and slpm is None:
            slpm = _parse_stat_value(_extract(re.search(r"SLpM:\s*([\d.%]+)", item_text)))
        if ("Str. Acc.:" in item_text or "Str. Acc:" in item_text) and str_acc is None:
            str_acc = _parse_stat_value(_extract(re.search(r"Str\.\s*Acc\.?\s*:\s*([\d.%]+)", item_text)))
        if "SApM:" in item_text and sapm is None:
            sapm = _parse_stat_value(_extract(re.search(r"SApM:\s*([\d.%]+)", item_text)))
        if ("Str. Def:" in item_text or "Str. Def.:" in item_text) and str_def is None:
            str_def = _parse_stat_value(_extract(re.search(r"Str\.\s*Def\.?\s*:\s*([\d.%]+)", item_text)))
        if ("TD Avg.:" in item_text or "TD Avg:" in item_text) and td_avg is None:
            td_avg = _parse_stat_value(_extract(re.search(r"TD\s*Avg\.?\s*:\s*([\d.%]+)", item_text)))
        if ("TD Acc.:" in item_text or "TD Acc:" in item_text) and td_acc is None:
            td_acc = _parse_stat_value(_extract(re.search(r"TD\s*Acc\.?\s*:\s*([\d.%]+)", item_text)))
        if ("TD Def.:" in item_text or "TD Def:" in item_text) and td_def is None:
            td_def = _parse_stat_value(_extract(re.search(r"TD\s*Def\.?\s*:\s*([\d.%]+)", item_text)))
        if ("Sub. Avg.:" in item_text or "Sub. Avg:" in item_text) and sub_avg is None:
            sub_avg = _parse_stat_value(_extract(re.search(r"Sub\.\s*Avg\.?\s*:\s*([\d.%]+)", item_text)))

    # Fallback: parsear desde todo el body (ufcstats puede usar clases distintas)
    if slpm is None and "SLpM:" in body_text:
        slpm = _parse_stat_value(_extract(re.search(r"SLpM:\s*([\d.%]+)", body_text)))
    if str_acc is None and ("Str. Acc.:" in body_text or "Str. Acc:" in body_text):
        str_acc = _parse_stat_value(_extract(re.search(r"Str\.\s*Acc\.?\s*:\s*([\d.%]+)", body_text)))
    if sapm is None and "SApM:" in body_text:
        sapm = _parse_stat_value(_extract(re.search(r"SApM:\s*([\d.%]+)", body_text)))
    if str_def is None and ("Str. Def:" in body_text or "Str. Def.:" in body_text):
        str_def = _parse_stat_value(_extract(re.search(r"Str\.\s*Def\.?\s*:\s*([\d.%]+)", body_text)))
    if td_avg is None and ("TD Avg.:" in body_text or "TD Avg:" in body_text):
        td_avg = _parse_stat_value(_extract(re.search(r"TD\s*Avg\.?\s*:\s*([\d.%]+)", body_text)))
    if td_acc is None and ("TD Acc.:" in body_text or "TD Acc:" in body_text):
        td_acc = _parse_stat_value(_extract(re.search(r"TD\s*Acc\.?\s*:\s*([\d.%]+)", body_text)))
    if td_def is None and ("TD Def.:" in body_text or "TD Def:" in body_text):
        td_def = _parse_stat_value(_extract(re.search(r"TD\s*Def\.?\s*:\s*([\d.%]+)", body_text)))
    if sub_avg is None and ("Sub. Avg.:" in body_text or "Sub. Avg:" in body_text):
        sub_avg = _parse_stat_value(_extract(re.search(r"Sub\.\s*Avg\.?\s*:\s*([\d.%]+)", body_text)))

    # Últimas 3 peleas (W/L): tabla de historial de peleas
    ultimas_peleas = []
    fight_rows = page.locator("tr.b-fight-details__table-row.b-fight-details__table-row__hover.js-fight-details-click")
    for i in range(min(fight_rows.count(), 3)):
        row = fight_rows.nth(i)
        first_col = row.locator("td").first
        if first_col.count():
            result_text = first_col.inner_text().strip().upper()
            if "WIN" in result_text:
                ultimas_peleas.append("W")
            elif "LOSS" in result_text:
                ultimas_peleas.append("L")
            elif "DRAW" in result_text or "NC" in result_text:
                ultimas_peleas.append("D")
            else:
                ultimas_peleas.append("—")

    # Fallback: si no se encontraron filas con esa clase, intentar con la tabla general
    if not ultimas_peleas:
        fight_rows_alt = page.locator("table.b-fight-details__table tr.b-fight-details__table-row")
        for i in range(min(fight_rows_alt.count(), 3)):
            row = fight_rows_alt.nth(i)
            first_col = row.locator("td").first
            if first_col.count():
                result_text = first_col.inner_text().strip().upper()
                if "WIN" in result_text:
                    ultimas_peleas.append("W")
                elif "LOSS" in result_text:
                    ultimas_peleas.append("L")
                elif "DRAW" in result_text or "NC" in result_text:
                    ultimas_peleas.append("D")
                else:
                    ultimas_peleas.append("—")

    return {
        "nombre": nombre,
        "record": record,
        "height": height,
        "weight": weight,
        "reach": reach,
        "stance": stance,
        "dob": dob,
        "ultimas_peleas": ultimas_peleas,
        "striking": {
            "slpm": slpm,
            "str_acc": str_acc,
            "sapm": sapm,
            "str_def": str_def,
        },
        "grappling": {
            "td_avg": td_avg,
            "td_acc": td_acc,
            "td_def": td_def,
            "sub_avg": sub_avg,
        },
    }


def guardar_json(resultado: dict) -> None:
    """Guarda el resultado únicamente en JSON."""
    json_path = os.path.join(OUTPUT_DIR, OUTPUT_JSON)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"Guardado: {json_path}")


def ejecutar_scraper() -> dict | None:
    """
    Ejecuta el scraping completo y retorna el resultado en memoria (sin guardar archivos).
    Retorna dict con evento, peleas, extraido_en; o None si falla.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            evento = extraer_evento_proximo(page)
            if not evento:
                return None

            peleas, fecha = extraer_peleas(page, evento["url_detalles"])
            evento["fecha"] = fecha

            perfiles_vistos = set()
            for pelea in peleas:
                for key in ("peleador_1", "peleador_2"):
                    p_info = pelea[key]
                    url = p_info["perfil"]
                    if url and url not in perfiles_vistos:
                        perfiles_vistos.add(url)
                        perfil_data = extraer_perfil_peleador(page, url)
                        if perfil_data:
                            p_info["estadisticas"] = perfil_data
                        time.sleep(REQUEST_DELAY)

            return {
                "evento": evento,
                "peleas": peleas,
                "extraido_en": datetime.now().isoformat(),
            }
        finally:
            browser.close()


def main() -> None:
    print("Scraper UFC Stats V1 - Evento próximo + estadísticas de peleadores")
    print("-" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            # 1. Obtener evento más próximo
            print("Obteniendo evento próximo...")
            evento = extraer_evento_proximo(page)
            if not evento:
                print("No se encontró ningún evento próximo.")
                return

            print(f"Evento: {evento['nombre']}")
            print(f"URL:   {evento['url_detalles']}")

            # 2. Extraer peleas (parejas + weight_class)
            print("\nExtrayendo peleas del evento...")
            peleas, fecha = extraer_peleas(page, evento["url_detalles"])
            evento["fecha"] = fecha
            print(f"Fecha: {evento['fecha']}")
            print(f"Peleas encontradas: {len(peleas)}")

            # 3. Extraer perfiles de cada peleador (evitar duplicados)
            perfiles_vistos = set()
            for pelea in peleas:
                for key in ("peleador_1", "peleador_2"):
                    p_info = pelea[key]
                    url = p_info["perfil"]
                    if url and url not in perfiles_vistos:
                        perfiles_vistos.add(url)
                        print(f"  Extrayendo perfil: {p_info['nombre']}...")
                        perfil_data = extraer_perfil_peleador(page, url)
                        if perfil_data:
                            p_info["estadisticas"] = perfil_data
                        time.sleep(REQUEST_DELAY)

            # 4. Guardar solo JSON
            resultado = {
                "evento": evento,
                "peleas": peleas,
                "extraido_en": datetime.now().isoformat(),
            }
            guardar_json(resultado)

            print("\n--- Resumen ---")
            for pelea in peleas:
                p1 = pelea["peleador_1"]["nombre"]
                p2 = pelea["peleador_2"]["nombre"]
                wc = pelea.get("weight_class", "")
                print(f"  • {p1} vs {p2} ({wc})")

        finally:
            browser.close()

    print("\nListo.")


if __name__ == "__main__":
    main()
