import urllib.parse
from pathlib import Path
from typing import List
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import config
from scrapers.base import (
    Product,
    human_delay,
    parse_price,
    parse_rating,
    parse_reviews_count,
)

stealth = Stealth()

class ShopeeScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.profile_dir = config.BASE_DIR / "shopee_profile"

    def search(self, term: str, max_items: int = 20) -> List[Product]:
        """
        Busca produtos na Shopee Brasil utilizando contexto persistente para manter sessão
        e contornar desafios de tráfego.
        """
        encoded_term = urllib.parse.quote_plus(term)
        url = f"https://shopee.com.br/search?keyword={encoded_term}"
        products = []
        captured_items_data = []

        def handle_response(response):
            try:
                if "search_items" in response.url and response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        data = response.json()
                        items = data.get("items") or data.get("data", {}).get("items") or []
                        for it in items:
                            item_info = it.get("item_basic") or it
                            if item_info and item_info.get("name"):
                                captured_items_data.append(item_info)
            except Exception:
                pass

        try:
            with sync_playwright() as p:
                # Usa contexto persistente para reutilizar cookies e tokens da Shopee
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    channel="chrome",
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--window-position=-2400,-2400",
                        "--window-size=1280,800",
                    ],
                    locale="pt-BR",
                    viewport={"width": 1280, "height": 800}
                )

                page = context.new_page()
                page.set_default_timeout(config.PAGE_TIMEOUT_MS)
                stealth.apply_stealth_sync(page)

                page.on("response", handle_response)
                page.goto(url, wait_until="domcontentloaded")
                human_delay(2.5, 4.0)

                # Verifica se caiu na tela de verificação de tráfego
                if "verify/traffic/error" in page.url or "captcha" in page.url.lower():
                    print("    [Shopee] A Shopee solicitou validação de tráfego humana.")
                    print("             (Dica: execute 'python main.py --login-shopee' uma vez para autenticar sua sessão).")
                    context.close()
                    return products

                # Rolagem suave
                page.evaluate("window.scrollBy(0, 600);")
                human_delay(1.5, 2.5)

                # Estratégia 1: Itens da API interna interceptados
                if captured_items_data:
                    for item in captured_items_data[:max_items]:
                        try:
                            title = item.get("name", "").strip()
                            if not title:
                                continue

                            raw_price = item.get("price", 0)
                            price = raw_price / 100000.0 if raw_price > 10000 else float(raw_price)

                            raw_orig = item.get("price_before_discount", 0)
                            orig_price = raw_orig / 100000.0 if raw_orig > 10000 else (float(raw_orig) if raw_orig else None)

                            raw_disc = item.get("raw_discount", 0)
                            discount_pct = float(raw_disc) if raw_disc else 0.0
                            if discount_pct == 0 and orig_price and orig_price > price:
                                discount_pct = round(((orig_price - price) / orig_price) * 100, 1)

                            rating_info = item.get("item_rating", {})
                            rating = float(rating_info.get("rating_star", 0.0))
                            rating_counts = rating_info.get("rating_count", [])
                            reviews_count = sum(rating_counts[1:]) if len(rating_counts) > 1 else item.get("historical_sold", 0)

                            shop_id = item.get("shopid")
                            item_id = item.get("itemid")
                            prod_url = f"https://shopee.com.br/product/{shop_id}/{item_id}" if shop_id and item_id else url

                            products.append(Product(
                                title=title,
                                store="Shopee",
                                current_price=price,
                                original_price=orig_price,
                                discount_percent=discount_pct,
                                rating=rating,
                                reviews_count=reviews_count,
                                url=prod_url,
                                free_shipping=bool(item.get("show_free_shipping")),
                            ))
                        except Exception:
                            continue

                # Estratégia 2: Fallback via DOM
                if not products:
                    cards = page.query_selector_all("li[data-sq='item'], div[data-sq='item'], a[data-sq='item']")
                    for card in cards[:max_items]:
                        try:
                            text_content = card.inner_text()
                            lines = [line.strip() for line in text_content.split("\n") if line.strip()]
                            if not lines:
                                continue

                            title = lines[0]
                            link_elem = card if card.evaluate("el => el.tagName") == "A" else card.query_selector("a")
                            href = link_elem.get_attribute("href") if link_elem else ""
                            prod_url = f"https://shopee.com.br{href}" if href and href.startswith("/") else href

                            price = None
                            for line in lines:
                                if "R$" in line:
                                    price = parse_price(line)
                                    if price:
                                        break
                            if not price:
                                continue

                            products.append(Product(
                                title=title,
                                store="Shopee",
                                current_price=price,
                                original_price=None,
                                discount_percent=0.0,
                                rating=parse_rating(text_content),
                                reviews_count=parse_reviews_count(text_content),
                                url=prod_url,
                                free_shipping=False
                            ))
                        except Exception:
                            continue

                context.close()

        except Exception as e:
            print(f"[Shopee] Erro ao processar '{term}': {e}")

        human_delay()
        return products

    def interactive_login(self):
        """Abre o navegador visível para o usuário resolver qualquer captcha e salvar cookies de sessão."""
        print("[*] Abrindo navegador visível para validação de sessão da Shopee...")
        print("    Resolva o captcha ou acesse sua conta na janela que se abrir.")
        print("    Pressione Enter no terminal quando tiver terminado para salvar.")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                channel="chrome",
                headless=False,
                locale="pt-BR"
            )
            page = context.new_page()
            page.goto("https://shopee.com.br")
            input("Pressione [ENTER] após a página carregar e resolver a verificação...")
            context.close()
        print("[✔] Sessão da Shopee salva com sucesso!")
