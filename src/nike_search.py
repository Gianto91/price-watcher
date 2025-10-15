from typing import List, Dict, Tuple
import tempfile, time
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
from .utils import parse_price_text

NIKE_HOME = "https://www.nike.com.pe"

def _safe_click(page, selectors):
    for sel in selectors:
        try:
            page.locator(sel).first.click(timeout=2000)
            return True
        except:
            pass
    return False

def search_prices_and_screenshot(query: str, full_page=True) -> Tuple[List[Dict], str]:
    """
    Devuelve (items, screenshot_path)
    items = list[ {name:str, price:float, url:str} ] ordenados por precio asc
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    screenshot_path = tmp.name
    tmp.close()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale="es-PE", viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        page.set_default_timeout(60000)
        page.set_extra_http_headers({"Accept-Language": "es-PE,es;q=0.9,en;q=0.8"})

        # 1) Ir a home y asegurarnos que exista <body>
        page.goto(NIKE_HOME, wait_until="domcontentloaded")
        try:
            page.wait_for_selector("body", timeout=10000)
        except:
            # Último recurso: espera corta
            page.wait_for_timeout(1500)

        # 2) Cerrar cookies si aparece (best-effort)
        _safe_click(page, [
            "button:has-text('Aceptar')",
            "button:has-text('Aceptar todo')",
            "button:has-text('Aceptar todas')",
            "button:has-text('Accept')"
        ])

        # 3) Abrir y ubicar el buscador (intento primario: input; fallback: navegar a URL de búsqueda)
        search = page.locator("input[placeholder*='Buscar' i], input[type='search']").first
        try:
            if not search.count():
                _safe_click(page, [
                    "button[aria-label*='Buscar' i]",
                    "a[aria-label*='Buscar' i]",
                    "button:has-text('Buscar')"
                ])
                search = page.locator("input[placeholder*='Buscar' i], input[type='search']").first

            # Asegurar que el input esté visible
            if search.count():
                search.wait_for(state="visible", timeout=15000)
                search.fill(query)
                search.press("Enter")
            else:
                # fallback: navegar directamente a la URL de búsqueda
                q = quote_plus(query)
                page.goto(f"{NIKE_HOME}/search?q={q}", wait_until="domcontentloaded")
        except Exception:
            # si algo falla con el input, usar la URL de búsqueda
            q = quote_plus(query)
            page.goto(f"{NIKE_HOME}/search?q={q}", wait_until="domcontentloaded")

        # 4) Esperar navegación y resultados (sin tocar document.body cuando puede ser null)
        page.wait_for_load_state("networkidle")
        # Esperar un indicio de precios "S/" de forma segura
        try:
            page.wait_for_selector("text=S/", timeout=45000)
        except:
            # A veces el sitio retrasa render; damos un respiro y seguimos
            page.wait_for_timeout(2000)

        # 5) Extraer tarjetas: recolectar textos de nodos y filtrar en Python (más robusto)
        q_lower = query.lower()
        nodes = page.eval_on_selector_all(
            "article, li, div",
            "els => els.map(e => ({text: e.innerText || '', href: (e.querySelector && e.querySelector('a[href]') ? e.querySelector('a[href]').href : null)}))",
        )
        cards = []
        want = []
        if 'dunk' in q_lower:
            want.append('dunk')
        if 'low' in q_lower:
            want.append('low')
        if 'retro' in q_lower:
            want.append('retro')
        import re
        for n in nodes:
            t = (n.get('text') or '').strip()
            tlow = t.lower()
            if any(w not in tlow for w in want):
                continue
            m = re.search(r"S/\s*[\d\.,]+", t)
            if not m:
                continue
            link = n.get('href') or page.url
            # try to get a short title from the first line
            title = t.split('\n')[0].strip()
            cards.append({'title': title, 'price': m.group(0), 'href': link})

        # 6) Screenshot SIEMPRE, para depurar si no hubo precios
        page.screenshot(path=screenshot_path, full_page=full_page)
        browser.close()

    # 7) Normalizar precios y ordenar
    items = []
    for c in cards or []:
        p = parse_price_text(c.get("price",""))
        if p is not None:
            items.append({"name": c.get("title","").strip(), "price": p, "url": c.get("href")})
    items.sort(key=lambda x: x["price"])
    return items, screenshot_path
