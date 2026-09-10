# -*- coding: utf-8 -*-
"""
Shopee Scraper para Nicho Pet (Banho & Tosa)
Desenvolvido para PromoPet Hunter
Extrai: Título, Preço, Desconto, Avaliação, Quantidade Vendida e Imagem.
Suporta Playwright com Anti-Bot e formatação canônica com ID de Afiliado 18391981133.
"""
import re
import time
import random
import urllib.parse
from typing import List, Optional
from playwright.sync_api import sync_playwright, Page

from scrapers.base import Product

class ShopeeScraper:
    """Scraper robusto para produtos de Banho & Tosa na Shopee Brasil."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.store = "shopee"
        self.affiliate_id = "18391981133"

    def search(self, query: str, max_items: int = 15) -> List[Product]:
        """
        Pesquisa produtos na Shopee ordenados pelos mais vendidos e com melhor reputação.
        """
        products: List[Product] = []
        clean_query = urllib.parse.quote(query)
        # Ordenação por mais vendidos (sortBy=sales)
        search_url = f"https://shopee.com.br/search?keyword={clean_query}&sortBy=sales"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--lang=pt-BR,pt"
                    ]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    locale="pt-BR",
                    viewport={"width": 1366, "height": 768}
                )
                page = context.new_page()
                page.set_default_timeout(35000)

                # Bloqueia fontes e mídias pesadas
                page.route(
                    "**/*",
                    lambda route: route.abort() if route.request.resource_type in ["media", "font"] else route.continue_()
                )

                page.goto(search_url, wait_until="domcontentloaded")
                time.sleep(3.0)

                # Fecha modal de login/pop-up se aparecer
                for close_sel in ["button.shopee-alert-popup__btn", "div.shopee-popup__close-btn", "svg[class*='shopee-svg-icon']"]:
                    try:
                        popup_btn = page.locator(close_sel).first
                        if popup_btn.count() > 0 and popup_btn.is_visible():
                            popup_btn.click()
                            time.sleep(0.5)
                    except Exception:
                        pass

                # Rola suavemente para baixo para carregar os cards virtuais da Shopee
                for _ in range(3):
                    page.mouse.wheel(0, 800)
                    time.sleep(1.0)

                # Seletores de itens de busca da Shopee
                card_selectors = [
                    "div.shopee-search-item-result__item",
                    "div[class*='col-xs-2-4']",
                    "li[class*='col-xs-2-4']",
                    "a[data-sqe='link']",
                    "a[href*='-i.']"
                ]

                cards = []
                for sel in card_selectors:
                    found = page.locator(sel).all()
                    if len(found) >= 4:
                        cards = found
                        break

                if not cards:
                    cards = page.locator("a[href*='-i.']").all()

                seen_urls = set()

                for card in cards:
                    if len(products) >= max_items:
                        break
                    try:
                        # Extrai a URL
                        url = None
                        if card.get_attribute("href"):
                            url = card.get_attribute("href")
                        else:
                            link_elem = card.locator("a[href*='-i.']").first
                            if link_elem.count() > 0:
                                url = link_elem.get_attribute("href")

                        if not url or "-i." not in url:
                            continue

                        if url.startswith("/"):
                            url = "https://shopee.com.br" + url

                        # Extrai Shop ID e Item ID da Shopee
                        match_id = re.search(r'-i\.(\d+)\.(\d+)', url)
                        if not match_id:
                            continue

                        shop_id, item_id = match_id.group(1), match_id.group(2)
                        canonical_url = f"https://shopee.com.br/product/{shop_id}/{item_id}"

                        if canonical_url in seen_urls:
                            continue
                        seen_urls.add(canonical_url)

                        card_text = card.inner_text()

                        # Título
                        title = ""
                        for t_sel in ["div[class*='truncate']", "div[data-sqe='name']", "span[class*='title']", "img[alt]"]:
                            t_elem = card.locator(t_sel).first
                            if t_elem.count() > 0:
                                title = t_elem.get_attribute("alt") if t_sel == "img[alt]" else t_elem.inner_text().strip()
                                if len(title) > 10:
                                    break

                        if not title:
                            lines = [l.strip() for l in card_text.split('\n') if len(l.strip()) > 10]
                            if lines:
                                title = lines[0]

                        if not title or len(title) < 8:
                            continue

                        # Preços
                        price_matches = re.findall(r'R\$\s*([\d\.,]+)', card_text)
                        parsed_prices = []
                        for pm in price_matches:
                            try:
                                val = float(pm.replace('.', '').replace(',', '.'))
                                if 3.0 <= val <= 25000.0:
                                    parsed_prices.append(val)
                            except ValueError:
                                continue

                        if not parsed_prices:
                            continue

                        current_price = min(parsed_prices)
                        original_price = max(parsed_prices) if len(parsed_prices) > 1 else current_price

                        # Desconto
                        discount_percent = 0.0
                        disc_match = re.search(r'-?(\d{1,2})%', card_text)
                        if disc_match:
                            discount_percent = float(disc_match.group(1))
                        elif original_price > current_price:
                            discount_percent = round(((original_price - current_price) / original_price) * 100, 1)

                        # Avaliação
                        rating = 4.8
                        rate_match = re.search(r'([45]\.\d)', card_text)
                        if rate_match:
                            rating = float(rate_match.group(1))

                        # Vendas
                        reviews_count = 250
                        sold_match = re.search(r'(\d+[\d\.,]*)\s*(?:mil|k)?\s*(?:vendido|vendidos)', card_text, re.IGNORECASE)
                        if sold_match:
                            raw_s = sold_match.group(1).replace('.', '').replace(',', '.')
                            try:
                                s_val = float(raw_s)
                                if "mil" in card_text.lower() or "k" in card_text.lower():
                                    s_val *= 1000
                                reviews_count = int(s_val)
                            except ValueError:
                                pass

                        # Imagem
                        image_url = ""
                        img_elem = card.locator("img").first
                        if img_elem.count() > 0:
                            src = img_elem.get_attribute("src") or img_elem.get_attribute("data-src") or ""
                            if src.startswith("//"):
                                src = "https:" + src
                            if "shopeesz.com" in src or "shopee.com" in src:
                                src = re.sub(r'_tn$', '', src)
                                image_url = src

                        prod = Product(
                            title=title.replace('\n', ' ').strip(),
                            price=current_price,
                            original_price=original_price if original_price > current_price else current_price,
                            discount_percent=discount_percent,
                            rating=rating,
                            reviews_count=reviews_count,
                            url=canonical_url,
                            image_url=image_url,
                            store="shopee"
                        )
                        products.append(prod)

                    except Exception:
                        continue

                context.close()
                browser.close()

        except Exception as e:
            print(f"      [!] Erro ao varrer Shopee via Playwright: {e}")

        return products
