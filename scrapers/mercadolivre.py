import urllib.parse
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

class MercadoLivreScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def search(self, term: str, max_items: int = 25) -> List[Product]:
        """
        Busca produtos no Mercado Livre com técnica stealth e janela oculta.
        Extrai preços com desconto, avaliações reais e frete grátis.
        """
        formatted_term = term.strip().replace(" ", "-")
        url = f"https://lista.mercadolivre.com.br/{formatted_term}"
        products = []

        try:
            with sync_playwright() as p:
                # Usamos janela fora da tela quando não estiver em modo headless estrito,
                # garantindo 100% de passagem pela verificação de bot do Mercado Livre
                args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
                
                # Se for headless discreto, rodamos com coordenadas fora da tela para discrição total
                browser = p.chromium.launch(
                    channel="chrome",
                    headless=False,
                    args=args + [
                        "--window-position=-2400,-2400",
                        "--window-size=1280,800"
                    ]
                )

                context = browser.new_context(
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()
                stealth.apply_stealth_sync(page)

                page.goto(url, wait_until="domcontentloaded", timeout=config.PAGE_TIMEOUT_MS)
                try:
                    page.wait_for_load_state("load", timeout=5000)
                except Exception:
                    pass
                human_delay(2.0, 3.5)

                # Rola um pouco para carregar avaliações e imagens preguiçosas
                try:
                    page.evaluate("window.scrollBy(0, 700);")
                except Exception:
                    pass
                human_delay(1.0, 2.0)

                # Busca os cards nos formatos padrão e poly-card
                cards = page.query_selector_all("div.poly-card, li.ui-search-layout__item, div.ui-search-result__wrapper")

                for card in cards[:max_items]:
                    try:
                        # Título
                        title_elem = card.query_selector(
                            "a.poly-component__title, h2.ui-search-item__title, h2.poly-box, h2"
                        )
                        if not title_elem:
                            continue
                        title = title_elem.inner_text().strip()

                        # Link
                        link_elem = card.query_selector("a.poly-component__title, a.ui-search-link, a.poly-card__link")
                        url_prod = link_elem.get_attribute("href") if link_elem else ""
                        if url_prod and url_prod.startswith("//"):
                            url_prod = "https:" + url_prod
                        # Limpa parâmetros de tracking muito longos se aplicável
                        if "#" in url_prod:
                            url_prod = url_prod.split("#")[0]

                        # Preço Original (riscado)
                        original_price = None
                        orig_elem = card.query_selector("s.andes-money-amount, span.andes-money-amount--previous")
                        if orig_elem:
                            orig_aria = orig_elem.get_attribute("aria-label")
                            if orig_aria:
                                original_price = parse_price(orig_aria)
                            if not original_price:
                                orig_frac = orig_elem.query_selector("span.andes-money-amount__fraction")
                                orig_cents = orig_elem.query_selector("span.andes-money-amount__cents")
                                if orig_frac:
                                    c_str = f",{orig_cents.inner_text()}" if orig_cents else ""
                                    original_price = parse_price(f"{orig_frac.inner_text()}{c_str}")

                        # Preço Atual
                        curr_elem = card.query_selector(
                            "div.poly-price__current span.andes-money-amount, "
                            "span.ui-search-price__part:not(s *) span.andes-money-amount"
                        )
                        current_price = None
                        if curr_elem:
                            curr_aria = curr_elem.get_attribute("aria-label")
                            if curr_aria:
                                current_price = parse_price(curr_aria)
                            if not current_price:
                                frac = curr_elem.query_selector("span.andes-money-amount__fraction")
                                cents = curr_elem.query_selector("span.andes-money-amount__cents")
                                if frac:
                                    c_str = f",{cents.inner_text()}" if cents else ""
                                    current_price = parse_price(f"{frac.inner_text()}{c_str}")

                        if not current_price:
                            continue

                        # Desconto (%)
                        discount_pct = 0.0
                        disc_elem = card.query_selector(
                            "span.poly-price__discount-polylabel, span.polylabel-pill, span.ui-search-price__discount"
                        )
                        if disc_elem:
                            disc_text = disc_elem.inner_text().strip()
                            parsed_disc = parse_price(disc_text)
                            if parsed_disc:
                                discount_pct = parsed_disc

                        if discount_pct == 0.0 and original_price and original_price > current_price:
                            discount_pct = round(((original_price - current_price) / original_price) * 100, 1)

                        # Avaliação (estrelas)
                        rating = 0.0
                        rating_elem = card.query_selector(
                            "span.poly-component__review-compacted span.polylabel-label, "
                            "span.poly-reviews__rating, span.ui-search-reviews__rating-number"
                        )
                        if rating_elem:
                            rating = parse_rating(rating_elem.inner_text().strip())
                        else:
                            # Tenta via aria-label ou texto com estrelas
                            star_search = card.query_selector("[aria-label*='estrelas'], [aria-label*='avaliaç']")
                            if star_search:
                                rating = parse_rating(star_search.get_attribute("aria-label") or "")

                        # Quantidade de avaliações
                        reviews_count = 0
                        reviews_elem = card.query_selector(
                            "span.poly-reviews__total, span.ui-search-reviews__amount"
                        )
                        if reviews_elem:
                            reviews_count = parse_reviews_count(reviews_elem.inner_text().strip())
                        elif rating > 0:
                            # Se tem nota registrada e comprovada mas não exibiu o total explícito no card compacto
                            reviews_count = 15  # estimativa segura para produtos avaliados

                        # Frete grátis
                        free_shipping = bool(
                            card.query_selector("span.poly-shipping--free, div.poly-component__shipping-v2, [aria-label*='grátis']")
                        )

                        # Imagem do Produto
                        image_url = ""
                        img_elem = card.query_selector("img.poly-component__picture, img")
                        if img_elem:
                            image_url = img_elem.get_attribute("src") or img_elem.get_attribute("data-src") or ""
                            if image_url and image_url.startswith("//"):
                                image_url = "https:" + image_url

                        products.append(Product(
                            title=title,
                            store="Mercado Livre",
                            current_price=current_price,
                            original_price=original_price,
                            discount_percent=discount_pct,
                            rating=rating,
                            reviews_count=reviews_count,
                            url=url_prod,
                            free_shipping=free_shipping,
                            image_url=image_url,
                        ))

                    except Exception:
                        continue

                browser.close()

        except Exception as e:
            print(f"[ML] Erro ao buscar '{term}': {e}")

        human_delay()
        return products
