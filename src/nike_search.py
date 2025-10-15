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
        print(f"[nike_search] Navegando a {NIKE_HOME} y buscando: {query}")
        search = page.locator("input[placeholder*='Buscar' i], input[type='search'], input[name='q']").first
        try:
            # Si no encontramos el input, intentamos abrir el panel de búsqueda via botones
            if not search.count():
                opened = _safe_click(page, [
                    "button[aria-label*='Buscar' i]",
                    "a[aria-label*='Buscar' i]",
                    "button:has-text('Buscar')",
                    "button[title*='Buscar' i]",
                ])
                if opened:
                    # re-evaluar el input
                    search = page.locator("input[placeholder*='Buscar' i], input[type='search'], input[name='q']").first

            # Si aparece el input, intentar llenarlo de forma robusta
            if search.count():
                print('[nike_search] Input de búsqueda encontrado, llenando...')
                try:
                    search.wait_for(state="visible", timeout=15000)
                    # Primer intento: método normal
                    search.fill(query)
                    search.press("Enter")
                except Exception:
                    # fallback: usar JS para fijar el valor y disparar eventos
                    print('[nike_search] Fallback: escribiendo valor mediante JS y disparando eventos')
                    page.evaluate('''(q) => {
                        const el = document.querySelector('input[placeholder*="Buscar" i], input[type="search"], input[name="q"]');
                        if (el) {
                            el.focus();
                            el.value = q;
                            el.dispatchEvent(new Event('input', {bubbles:true}));
                            el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'}));
                        }
                    }''', query)
                    # A veces es necesario presionar Enter desde la página
                    try:
                        page.keyboard.press('Enter')
                    except Exception:
                        pass
            else:
                # fallback: navegar directamente a la URL de búsqueda
                print('[nike_search] No se encontró input; navegando a URL de búsqueda')
                q = quote_plus(query)
                resp = page.goto(f"{NIKE_HOME}/search?q={q}", wait_until="domcontentloaded")
                # Si la página devuelve 4xx/5xx (ej. 404), reintentar con una query ampliada
                try:
                    status = resp.status if resp else 200
                except Exception:
                    status = 200
                if status >= 400:
                    alt_q = quote_plus(f"nike {query} hombre")
                    print(f"[nike_search] Página falló con status {status}, reintentando con '{alt_q}'")
                    page.goto(f"{NIKE_HOME}/search?q={alt_q}", wait_until="domcontentloaded")
        except Exception as exc:
            print(f'[nike_search] Excepción durante búsqueda: {exc}')
            # si algo falla con el input, usar la URL de búsqueda (y reintentar con variante si falla)
            q = quote_plus(query)
            resp = page.goto(f"{NIKE_HOME}/search?q={q}", wait_until="domcontentloaded")
            try:
                status = resp.status if resp else 200
            except Exception:
                status = 200
            if status >= 400:
                alt_q = quote_plus(f"nike {query} hombre")
                print(f"[nike_search] Reintentando con '{alt_q}'")
                page.goto(f"{NIKE_HOME}/search?q={alt_q}", wait_until="domcontentloaded")

        # 4) Esperar navegación y resultados: primero intentar detectar tarjetas de producto
        # Evitamos `networkidle` que puede bloquear si el sitio carga recursos largos
        product_wait_selectors = "article, .product-card, .product-grid__item, .product-tile, div.productcell"
        try:
            page.wait_for_selector(product_wait_selectors, timeout=45000)
        except Exception:
            # Si no aparecen tarjetas, intentar detectar un indicio de precios "S/"
            try:
                page.wait_for_selector("text=S/", timeout=30000)
            except Exception:
                # Ultimo recurso: espera corta y continuar
                page.wait_for_timeout(2000)

        # 5) Extraer tarjetas: priorizar selectores de tarjetas de producto para evitar texto irrelevante
        q_lower = query.lower()
        product_selectors = [
            'article.product',
            'article.product-card',
            '.product-card',
            '.product-grid__item',
            'li.product',
            'div.product-card',
            'div.product-tile',
            'div.productcell',
            'article',
        ]
        sel = ','.join(product_selectors)
        # Evaluate on likely product tiles; extract title, price text, href and full text
        nodes = page.eval_on_selector_all(
            sel,
            '''els => els.map(e => {
                const text = (e.innerText || '').trim();
                const linkEl = e.querySelector('a[href]');
                const href = linkEl ? linkEl.href : (location.href || null);
                // Try to get a title from common headings
                const titleEl = e.querySelector('h3,h2,a[title],a');
                const title = titleEl ? (titleEl.innerText||'').trim() : (text.split('\n')[0]||'').trim();
                // Try to find a price-like substring
                const m = text.match(/S\/\s*[\d\.,]+/i);
                const price = m ? m[0] : null;
                return {title, price, href, text};
            })''',
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
            # include the full text to allow precise matching later
            cards.append({'title': title, 'price': m.group(0), 'href': link, 'text': t})

        # 6) Screenshot SIEMPRE, para depurar si no hubo precios
        page.screenshot(path=screenshot_path, full_page=full_page)
        browser.close()

    # 7) Normalizar precios y ordenar
    items = []
    seen = set()
    for c in cards or []:
        p = parse_price_text(c.get("price",""))
        if p is None:
            continue
        title = c.get("title","").strip()
        href = c.get("href") or ""
        text = c.get("text","")
        # Filtrar nodos obvios no-producto
        tl = title.lower()
        if not title or len(title) < 3:
            continue
        if 'saltar al contenido' in tl or 'buscar' == tl:
            continue
        # Deduplicar
        key = f"{title}|{p}|{href}"
        if key in seen:
            continue
        seen.add(key)
        items.append({"name": title, "price": p, "url": href, "text": text})
    items.sort(key=lambda x: x["price"])
    return items, screenshot_path
