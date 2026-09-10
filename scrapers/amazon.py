import urllib.parse
from typing import List
from playwright.sync_api import sync_playwright, BrowserContext
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

class AmazonScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def search(self, term: str, max_items: int = 25) -> List[Product]:
        """Busca produtos na Amazon Brasil usando navegador com perfil stealth anti-bloqueio."""
        encoded_term = urllib.parse.quote_plus(term)
        url = f"https://www.amazon.com.br/s?k={encoded_term}"
        products = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-infobars",
                    ]
                )
                
                context: BrowserContext = browser.new_context(
                    user_agent=config.USER_AGENTS[0],
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    viewport={"width": 1366, "height": 768},
                    device_scale_factor=1,
                )

                page = context.new_page()
                page.set_default_timeout(config.PAGE_TIMEOUT_MS)
                stealth.apply_stealth_sync(page)

                # Acessa a página de busca
                page.goto(url, wait_until="domcontentloaded")
                human_delay(2.0, 3.5)

                # Rola suavemente para baixo para carregar mais itens
                page.evaluate("window.scrollBy(0, 700);")
                human_delay(1.0, 2.0)

                # Verifica se caiu em CAPTCHA
                page_content = page.content()
                if "Digite os caracteres que você vê abaixo" in page_content or "api-services-support@amazon.com" in page_content:
                    print(f"[Amazon] CAPTCHA detectado para o termo '{term}'. Pulando com segurança.")
                    browser.close()
                    return products

                # Seleciona os cartões de resultado da Amazon
                cards = page.query_selector_all("div[data-component-type='s-search-result']")

                for card in cards[:max_items]:
                    try:
                        # Título
                        title_elem = card.query_selector("h2 span, h2 a span")
                        if not title_elem:
                            continue
                        title = title_elem.inner_text().strip()

                        # Link
                        link_elem = card.query_selector("h2 a, a.a-link-normal")
                        rel_url = link_elem.get_attribute("href") if link_elem else ""
                        if rel_url and rel_url.startswith("/"):
                            product_url = f"https://www.amazon.com.br{rel_url.split('?')[0]}"
                        else:
                            product_url = rel_url

                        # Preço Atual
                        price_elem = card.query_selector("span.a-price:not(.a-text-price) span.a-offscreen")
                        if not price_elem:
                            price_elem = card.query_selector("span.a-price-whole")
                        if not price_elem:
                            continue
                        current_price = parse_price(price_elem.inner_text())
                        if not current_price:
                            continue

                        # Preço Original (De)
                        original_price = None
                        orig_elem = card.query_selector("span.a-price.a-text-price span.a-offscreen")
                        if orig_elem:
                            original_price = parse_price(orig_elem.inner_text())

                        # Desconto Percentual
                        discount_pct = 0.0
                        if original_price and original_price > current_price:
                            discount_pct = round(((original_price - current_price) / original_price) * 100, 1)

                        # Avaliação (Estrelas)
                        rating = 0.0
                        star_elem = card.query_selector("i[class*='star'], i.a-icon-star-small, i.a-icon-star")
                        if star_elem:
                            star_text = star_elem.inner_text().strip()
                            rating = parse_rating(star_text)
                        if rating == 0.0:
                            aria_elem = card.query_selector("[aria-label*='estrelas'], [aria-label*='stars']")
                            if aria_elem:
                                rating = parse_rating(aria_elem.get_attribute("aria-label") or "")

                        # Quantidade de Avaliações
                        reviews_count = 0
                        reviews_elem = card.query_selector("span.s-underline-text, a[href*='#customerReviews'] span")
                        if reviews_elem:
                            reviews_count = parse_reviews_count(reviews_elem.inner_text())

                        # Frete Prime / Grátis
                        free_shipping = bool(
                            card.query_selector("i.a-icon-prime") or
                            "Frete GRÁTIS" in card.inner_text()
                        )

                        # Imagem do Produto
                        image_url = ""
                        img_elem = card.query_selector("img.s-image, img")
                        if img_elem:
                            image_url = img_elem.get_attribute("src") or ""

                        products.append(Product(
                            title=title,
                            store="Amazon",
                            current_price=current_price,
                            original_price=original_price,
                            discount_percent=discount_pct,
                            rating=rating,
                            reviews_count=reviews_count,
                            url=product_url,
                            free_shipping=free_shipping,
                            image_url=image_url,
                        ))

                    except Exception:
                        continue

                browser.close()

        except Exception as e:
            print(f"[Amazon] Erro ao processar '{term}': {e}")

        human_delay()
        return products
