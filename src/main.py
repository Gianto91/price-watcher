import os, sys
from datetime import datetime
from .nike_search import search_prices_and_screenshot
from .notify import send_message, send_photo

QUERY = os.getenv("QUERY", "Nike Dunk Low Retro")
# Default threshold: 549.90 soles
THRESHOLD = float(os.getenv("THRESHOLD", "549.90"))
BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")
SEND_SHOT_ALWAYS = os.getenv("SEND_SCREENSHOT_ALWAYS","false").lower() == "true"

def main():
    if not BOT or not CHAT:
        print("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID", file=sys.stderr)
        sys.exit(2)

    items, shot = search_prices_and_screenshot(QUERY, full_page=True)
    now = datetime.utcnow().isoformat(timespec="seconds")

    if not items:
        msg = f"🔎 {now} | Sin resultados con precio para '{QUERY}' en Nike Perú."
        send_message(BOT, CHAT, msg)
        try: send_photo(BOT, CHAT, shot, caption=msg)
        finally:
            try: os.remove(shot)
            except: pass
        return

    # Intentar localizar productos que contengan el texto exacto buscado
    target_lines = ["nike dunk low retro", "zapatillas para hombre"]
    matched = []
    for it in items:
        text = (it.get("text") or "").lower()
        if all(t in text for t in target_lines):
            matched.append(it)

    if matched:
        matched.sort(key=lambda x: x["price"])
        best = matched[0]
    else:
        best = items[0]
    resumen = "\n".join([f"- S/ {i['price']:.2f} — {i['name']}" for i in items[:5]])

    base = (f"🛒 Monitoreo Nike\n"
            f"Consulta: {QUERY}\n"
            f"Mejor precio: S/ {best['price']:.2f}\n"
            f"Umbral: S/ {THRESHOLD:.2f}\n"
            f"Producto: {best['name']}\n"
            f"Link: {best['url']}\n\nTop 5:\n{resumen}")

    if best["price"] < THRESHOLD:
        alert = f"⚠️ ¡Bajó del umbral! S/ {best['price']:.2f} < S/ {THRESHOLD:.2f}\n{best['url']}"
        send_message(BOT, CHAT, alert)

    if SEND_SHOT_ALWAYS or best["price"] < THRESHOLD:
        try: send_photo(BOT, CHAT, shot, caption=base)
        finally:
            try: os.remove(shot)
            except: pass
    else:
        # si no enviamos screenshot, al menos enviamos el resumen
        send_message(BOT, CHAT, base)

if __name__ == "__main__":
    main()
