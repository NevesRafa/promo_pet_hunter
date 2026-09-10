# -*- coding: utf-8 -*-
"""
PromoPet Hunter - Caçador Contínuo Furtivo Sem Limite (4 Lojas)
Mercado Livre + Amazon + AliExpress + Shopee

Arquitetura Anti-Conflito e Anti-Ban:
1. Garimpo das 4 lojas de forma sequencial com WhatsApp 100% FECHADO.
2. Scrapers nativos seguros para Shopee e AliExpress sem risco de 'context destroyed'.
3. Termos de busca direcionados para o que cada loja tem de melhor no Nicho Pet / Banho & Tosa.
4. Normalização inteligente de lojas e atributos (suporta 'price' e 'current_price' sem erros).
5. Filtro Pet aprimorado (aceita 'Cheirinho de Bebê' de colônias pet legítimas).
6. Priorização inteligente por desconto e reputação, garantindo sempre 3 a 4 super ofertas.
7. Se um lote estiver vazio, NÃO abre o WhatsApp; aguarda apenas 3 minutos para nova tentativa.
8. WhatsApp Web com digitação humana, foto real ou prévia, e pausas orgânicas.
"""
import os
import sys
import time
import random
import re
import json
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import config
from scrapers.base import Product
from scrapers.mercadolivre import MercadoLivreScraper
from scrapers.amazon import AmazonScraper
from filters import deduplicate_products
from templates import format_single_deal_message
from whatsapp_sender import WhatsAppSender
from media_manager import MediaManager
from playwright.sync_api import sync_playwright, Page

# ==============================================================================
# UTILITÁRIOS UNIVERSAIS DE PREÇO E PRODUTO (COMPATIBILIDADE 100% BLINDADA)
# ==============================================================================
def get_preco_produto(p) -> float:
    """Extrai o preço de qualquer objeto Product sem estourar AttributeError."""
    for attr in ("price", "current_price", "raw_price", "valor", "original_price"):
        val = getattr(p, attr, None)
        if val is not None:
            try:
                f_val = float(val)
                if f_val > 0:
                    return f_val
            except (ValueError, TypeError):
                continue
    return 0.0

def normalizar_produto(p: Product) -> Product:
    """Garante que tanto .price quanto .current_price existam em qualquer objeto."""
    preco = get_preco_produto(p)
    try:
        p.price = preco
    except Exception:
        pass
    try:
        p.current_price = preco
    except Exception:
        pass
    try:
        p.discount_percent = float(getattr(p, "discount_percent", 0.0) or 0.0)
    except Exception:
        pass
    try:
        p.rating = float(getattr(p, "rating", 4.8) or 4.8)
    except Exception:
        pass
    return p

def criar_produto_seguro(
    title: str,
    price: float,
    orig_price: float,
    disc_pct: float,
    rating: float,
    reviews_count: int,
    url: str,
    image_url: str,
    store: str
) -> Product:
    """Cria um objeto Product compatível com qualquer variante da classe no repo."""
    try:
        prod = Product(
            title=title,
            current_price=price,
            original_price=orig_price,
            discount_percent=disc_pct,
            rating=rating,
            reviews_count=reviews_count,
            url=url,
            image_url=image_url,
            store=store
        )
    except TypeError:
        try:
            prod = Product(
                title=title,
                price=price,
                original_price=orig_price,
                discount_percent=disc_pct,
                rating=rating,
                reviews_count=reviews_count,
                url=url,
                image_url=image_url,
                store=store
            )
        except TypeError:
            prod = Product(title=title, url=url, store=store)

    prod.price = price
    prod.current_price = price
    prod.original_price = orig_price
    prod.discount_percent = disc_pct
    prod.rating = rating
    prod.reviews_count = reviews_count
    prod.image_url = image_url
    prod.store = store
    return prod

# ==============================================================================
# SCRAPER NATIVO SEGURO: SHOPEE BRASIL (SEM PAGE.EVALUATE, 100% LOCATORS)
# ==============================================================================
class SafeShopeeScraper:
    """Scraper blindado da Shopee que não quebra em navegações dinâmicas."""
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.store = "shopee"
        self.affiliate_id = getattr(config, "SHOPEE_AFFILIATE_ID", "18391981133")

    def search(self, query: str, max_items: int = 12) -> List[Product]:
        products: List[Product] = []
        clean_query = urllib.parse.quote(query)
        search_url = f"https://shopee.com.br/search?keyword={clean_query}&sortBy=sales"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--lang=pt-BR,pt"]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    locale="pt-BR",
                    viewport={"width": 1366, "height": 768}
                )
                page = context.new_page()
                page.set_default_timeout(35000)
                page.route("**/*", lambda r: r.abort() if r.request.resource_type in ["media", "font"] else r.continue_())

                try:
                    page.goto(search_url, wait_until="domcontentloaded")
                except Exception:
                    pass

                time.sleep(4.0)

                # Fecha popups se existirem
                for close_sel in ["button.shopee-alert-popup__btn", "div.shopee-popup__close-btn"]:
                    try:
                        btn = page.locator(close_sel).first
                        if btn.count() > 0 and btn.is_visible():
                            btn.click()
                            time.sleep(0.5)
                    except Exception:
                        pass

                for _ in range(3):
                    page.mouse.wheel(0, 800)
                    time.sleep(0.8)

                cards = page.locator("a[data-sqe='link'], a[href*='-i.'], div.shopee-search-item-result__item a").all()
                seen_urls = set()

                for card in cards:
                    if len(products) >= max_items:
                        break
                    try:
                        url = card.get_attribute("href") or ""
                        if "-i." not in url:
                            continue
                        if url.startswith("/"):
                            url = "https://shopee.com.br" + url

                        m_id = re.search(r'-i\.(\d+)\.(\d+)', url)
                        if not m_id:
                            continue
                        shop_id, item_id = m_id.group(1), m_id.group(2)
                        can_url = f"https://shopee.com.br/product/{shop_id}/{item_id}"
                        if can_url in seen_urls:
                            continue
                        seen_urls.add(can_url)

                        card_text = card.inner_text()
                        lines = [l.strip() for l in card_text.split('\n') if len(l.strip()) > 8]
                        title = lines[0] if lines else ""

                        p_matches = re.findall(r'R\$\s*([\d\.,]+)', card_text)
                        parsed = []
                        for pm in p_matches:
                            try:
                                v = float(pm.replace('.', '').replace(',', '.'))
                                if 3.0 <= v <= 20000.0:
                                    parsed.append(v)
                            except ValueError:
                                pass

                        if not parsed:
                            continue
                        curr_price = min(parsed)
                        orig_price = max(parsed) if len(parsed) > 1 else curr_price

                        disc_pct = 0.0
                        m_disc = re.search(r'-?(\d{1,2})%', card_text)
                        if m_disc:
                            disc_pct = float(m_disc.group(1))
                        elif orig_price > curr_price:
                            disc_pct = round(((orig_price - curr_price) / orig_price) * 100, 1)

                        rate = 4.8
                        m_rate = re.search(r'([45]\.\d)', card_text)
                        if m_rate:
                            rate = float(m_rate.group(1))

                        img_url = ""
                        im_el = card.locator("img").first
                        if im_el.count() > 0:
                            src = im_el.get_attribute("src") or im_el.get_attribute("data-src") or ""
                            if src.startswith("//"):
                                src = "https:" + src
                            if "shopeesz.com" in src or "shopee.com" in src:
                                src = re.sub(r'_tn$', '', src)
                                img_url = src

                        prod = criar_produto_seguro(
                            title=title.replace('\n', ' ').strip(),
                            price=curr_price,
                            orig_price=orig_price,
                            disc_pct=disc_pct,
                            rating=rate,
                            reviews_count=180,
                            url=can_url,
                            image_url=img_url,
                            store="shopee"
                        )
                        products.append(prod)
                    except Exception:
                        continue

                context.close()
                browser.close()
        except Exception as e:
            print(f"      [!] Shopee Playwright: {e}")
        return products

# ==============================================================================
# SCRAPER NATIVO SEGURO: ALIEXPRESS CHOICE
# ==============================================================================
class SafeAliExpressScraper:
    """Scraper blindado do AliExpress focado em ferramentas de tosa."""
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.store = "aliexpress"
        self.tracking_id = getattr(config, "ALIEXPRESS_TRACKING_ID", "n3v35")

    def search(self, query: str, max_items: int = 12) -> List[Product]:
        products: List[Product] = []
        clean_query = urllib.parse.quote(query)
        search_url = f"https://pt.aliexpress.com/w/wholesale-{clean_query}.html?g=y&SearchText={clean_query}&sortType=total_tranpro_desc"
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--lang=pt-BR,pt"]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    locale="pt-BR",
                    viewport={"width": 1366, "height": 768}
                )
                page = context.new_page()
                page.set_default_timeout(35000)
                page.route("**/*", lambda r: r.abort() if r.request.resource_type in ["media", "font"] else r.continue_())

                try:
                    page.goto(search_url, wait_until="domcontentloaded")
                except Exception:
                    pass

                time.sleep(3.5)

                for _ in range(3):
                    page.mouse.wheel(0, 800)
                    time.sleep(0.8)

                cards = page.locator("a[href*='/item/']").all()
                seen_urls = set()

                for card in cards:
                    if len(products) >= max_items:
                        break
                    try:
                        url = card.get_attribute("href") or ""
                        if "/item/" not in url:
                            continue
                        m_id = re.search(r'/item/(\d+)\.html', url)
                        if not m_id:
                            continue
                        item_id = m_id.group(1)
                        can_url = f"https://pt.aliexpress.com/item/{item_id}.html"
                        if can_url in seen_urls:
                            continue
                        seen_urls.add(can_url)

                        title = ""
                        for t_sel in ["h3", "h1", "div[class*='title']", "span[class*='title']", "img[alt]"]:
                            el = card.locator(t_sel).first
                            if el.count() > 0:
                                title = el.get_attribute("alt") if t_sel == "img[alt]" else el.inner_text().strip()
                                if len(title) > 10:
                                    break
                        if len(title) < 8:
                            continue

                        card_text = card.inner_text()
                        p_matches = re.findall(r'R\$\s*([\d\.,]+)', card_text)
                        parsed = []
                        for pm in p_matches:
                            try:
                                v = float(pm.replace('.', '').replace(',', '.'))
                                if 2.0 <= v <= 20000.0:
                                    parsed.append(v)
                            except ValueError:
                                pass

                        if not parsed:
                            continue
                        curr_price = min(parsed)
                        orig_price = max(parsed) if len(parsed) > 1 else curr_price

                        disc_pct = 0.0
                        m_disc = re.search(r'-?(\d{1,2})%', card_text)
                        if m_disc:
                            disc_pct = float(m_disc.group(1))
                        elif orig_price > curr_price:
                            disc_pct = round(((orig_price - curr_price) / orig_price) * 100, 1)

                        rate = 4.7
                        m_rate = re.search(r'([45]\.\d)', card_text)
                        if m_rate:
                            rate = float(m_rate.group(1))

                        img_url = ""
                        im_el = card.locator("img").first
                        if im_el.count() > 0:
                            src = im_el.get_attribute("src") or im_el.get_attribute("data-src") or ""
                            if src.startswith("//"):
                                src = "https:" + src
                            if "alicdn.com" in src:
                                src = re.sub(r'_\d+x\d+.*$', '', src)
                                img_url = src

                        prod = criar_produto_seguro(
                            title=title.replace('\n', ' ').strip(),
                            price=curr_price,
                            orig_price=orig_price,
                            disc_pct=disc_pct,
                            rating=rate,
                            reviews_count=120,
                            url=can_url,
                            image_url=img_url,
                            store="aliexpress"
                        )
                        products.append(prod)
                    except Exception:
                        continue

                context.close()
                browser.close()
        except Exception as e:
            print(f"      [!] AliExpress Playwright: {e}")
        return products

# ==============================================================================
# HISTÓRICO LOCAL DE ENVIADOS (GARANTE ZERO REPETIÇÃO)
# ==============================================================================
HISTORICO_FILE = Path("historico_enviados.json")

def carregar_historico() -> Set[str]:
    if not HISTORICO_FILE.exists():
        return set()
    try:
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data)
    except Exception:
        return set()

def salvar_historico(historico: Set[str]):
    try:
        with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
            json.dump(list(historico), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f" [!] Erro ao salvar histórico: {e}")

# ==============================================================================
# FILTRO PET RIGOROSO COM INTELIGÊNCIA DE CHEIRINHO DE BEBÊ
# ==============================================================================
PALAVRAS_PROIBIDAS_NAO_PET = [
    # Automotivo
    "automotivo", "automotiva", "carro", "veicular", "moto", "lava auto", "vonixx",
    "cera", "pneu", "lataria", "motor", "parabrisa", "v-floc", "pretinho", "detailer",
    # Cabelo humano / Salão de beleza
    "cabelo humano", "capilar", "salao de beleza", "salão", "cabeleireiro", "cabeleireira",
    "progressiva", "botox capilar", "alisamento", "tintura", "mechas", "barba", "barbeiro",
    "escova progressiva", "l'oréal", "wella", "haskell",
    # Bebê / Criança (estrito para não barrar perfume pet cheirinho de bebê)
    "infantil", "berco", "berço", "fralda descartavel", "maternidade", "recem-nascido",
    "recém-nascido", "banheira de bebe", "banheira infantil", "chupeta", "mamadeira",
    # Cozinha / Casa / Outros
    "panela", "cozinha", "culinaria", "culinária", "costura", "alfaiate", "maca de massagem",
    "mesa de passar", "tatuagem", "tatuador", "estetica facial", "estética facial", "depilacao",
    "depilação", "smartphone", "celular", "capinha"
]

PALAVRAS_OBRIGATORIAS_PET = [
    "pet", "pets", "cão", "caes", "cães", "cao", "cachorro", "cachorros", "cadela",
    "gato", "gatos", "felino", "felinos", "canino", "caninos", "tosa", "tosador",
    "tosadora", "banho e tosa", "banho tosa", "petshop", "pet shop", "pelagem",
    "subpelo", "sub-pelo", "animal", "animais", "veterinario", "veterinaria",
    "rasqueadeira", "desembolo", "desembolador", "desemboçador", "soprador",
    "secador pet", "maquina tosa", "máquina tosa", "lamina tosa", "lâmina tosa",
    "canil", "toalha pet", "coleira contencao", "focinheira", "shampoo cães", "shampoo pet",
    "pente tosa", "tesoura tosa", "adaptador lamina", "corta unha pet",
    "laco pet", "laço pet", "bandana pet", "gravata pet", "colonia pet", "perfume pet"
]

def validar_produto_pet(produto: Product) -> bool:
    titulo = produto.title.lower()
    for termo_proibido in PALAVRAS_PROIBIDAS_NAO_PET:
        if re.search(r'\b' + re.escape(termo_proibido) + r'\b', titulo):
            return False
    return any(termo_pet in titulo for termo_pet in PALAVRAS_OBRIGATORIAS_PET)

# ==============================================================================
# NORMALIZADOR UNIVERSAL DE LOJAS (EVITA ERRO COM ESPAÇOS)
# ==============================================================================
def normalizar_loja(store_str: str) -> str:
    s = (store_str or "").lower().replace(" ", "").replace("_", "").replace("-", "")
    if "mercado" in s or "meli" in s:
        return "mercadolivre"
    if "amazon" in s:
        return "amazon"
    if "ali" in s:
        return "aliexpress"
    if "shopee" in s:
        return "shopee"
    return "outros"

# ==============================================================================
# LINKS DE AFILIADOS OFICIAIS
# ==============================================================================
def construir_link_meli_seguro(url_original: str) -> str:
    if not url_original:
        return url_original
    mlb_match = re.search(r'(MLB-?\d{8,14})', url_original, re.IGNORECASE)
    if mlb_match:
        mlb_code = mlb_match.group(1).upper().replace('-', '')
        base_url = f"https://produto.mercadolivre.com.br/MLB-{mlb_code}"
    elif "/p/MLB" in url_original:
        p_match = re.search(r'/p/(MLB\d+)', url_original, re.IGNORECASE)
        base_url = f"https://www.mercadolivre.com.br/p/{p_match.group(1).upper()}" if p_match else url_original.split('?')[0]
    else:
        base_url = url_original.split('?')[0]

    tool_id = getattr(config, "MELI_TOOL", "85415830")
    word_id = getattr(config, "MELI_WORD", "neves_rafael")
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}matt_tool={tool_id}&matt_word={word_id}"

def construir_link_amazon_seguro(url_original: str) -> str:
    tag = getattr(config, "AMAZON_TAG", "n3v35-20")
    asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url_original, re.IGNORECASE)
    if asin_match:
        asin = asin_match.group(1).upper()
        return f"https://www.amazon.com.br/dp/{asin}?tag={tag}"
    sep = "&" if "?" in url_original else "?"
    return f"{url_original}{sep}tag={tag}"

def construir_link_aliexpress_seguro(url_original: str) -> str:
    tracking_id = getattr(config, "ALIEXPRESS_TRACKING_ID", "n3v35")
    item_match = re.search(r'/item/(\d+)\.html', url_original)
    if item_match:
        item_id = item_match.group(1)
        return f"https://pt.aliexpress.com/item/{item_id}.html?tracking_id={tracking_id}&aff_platform=portals-tool"
    sep = "&" if "?" in url_original else "?"
    return f"{url_original}{sep}tracking_id={tracking_id}"

def construir_link_shopee_seguro(url_original: str) -> str:
    aff_id = getattr(config, "SHOPEE_AFFILIATE_ID", "18391981133")
    match_id = re.search(r'product/(\d+)/(\d+)', url_original)
    if match_id:
        shop_id, item_id = match_id.group(1), match_id.group(2)
        base_url = f"https://shopee.com.br/product/{shop_id}/{item_id}"
        return f"{base_url}?af_siteid={aff_id}&pid=affiliates"
    sep = "&" if "?" in url_original else "?"
    return f"{url_original}{sep}af_siteid={aff_id}&pid=affiliates"

def aplicar_links_afiliados_robusto(produtos: List[Product]) -> List[Product]:
    for p in produtos:
        store = normalizar_loja(p.store)
        if store == "mercadolivre":
            p.url = construir_link_meli_seguro(p.url)
        elif store == "amazon":
            p.url = construir_link_amazon_seguro(p.url)
        elif store == "aliexpress":
            p.url = construir_link_aliexpress_seguro(p.url)
        elif store == "shopee":
            p.url = construir_link_shopee_seguro(p.url)
    return produtos

# ==============================================================================
# BANCOS DE TERMOS INTELIGENTES DIRECIONADOS POR LOJA
# ==============================================================================
TERMOS_MERCADOLIVRE = [
    "colonia pet fixacao profissional",
    "shampoo pet caes 5 litros",
    "soprador pet banho e tosa",
    "maquina de tosa caes profissional",
    "mesa de tosa dobravel pet",
    "secador pet profissional tosa",
    "lamina de tosa 10 profissional",
    "toalha alta absorcao pet banho tosa",
    "perfume pet duradouro caes"
]

TERMOS_AMAZON = [
    "shampoo pet caes 5 litros",
    "condicionador pet caes 5 litros",
    "mascara hidratacao pet profissional",
    "rasqueadeira profissional pet",
    "tesoura tosa curva pet",
    "maquina tosa caes profissional",
    "alicate cortador unha pet cachorro",
    "desembolador de pelos pet"
]

TERMOS_ALIEXPRESS = [
    "maquina tosa pet profissional",
    "tesoura tosa tubarao",
    "tesoura tosa curva",
    "pente aco tosa cao",
    "laminas tosa pet",
    "rasqueadeira autolimpante cao",
    "lixa unha pet cachorro",
    "kit tosa tesouras pet"
]

TERMOS_SHOPEE = [
    "lacos pet banho e tosa atacado",
    "bandanas pet atacado banho tosa",
    "gravata pet atacado",
    "shampoo pet 5 litros",
    "perfume pet fixacao",
    "toalha banho pet alta absorcao",
    "rasqueadeira pet cao"
]

def extrair_id_unico(produto: Product) -> str:
    url = produto.url
    m_mlb = re.search(r'(MLB\d+)', url)
    if m_mlb:
        return f"ml_{m_mlb.group(1)}"
    m_asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url)
    if m_asin:
        return f"amz_{m_asin.group(1)}"
    m_ali = re.search(r'/item/(\d+)\.html', url)
    if m_ali:
        return f"ali_{m_ali.group(1)}"
    m_shp = re.search(r'product/(\d+/\d+)', url)
    if m_shp:
        return f"shp_{m_shp.group(1)}"
    return url.split('?')[0]

# ==============================================================================
# GARIMPO ISOLADO: 4 LOJAS (SEM NENHUM BROWSER DO WHATSAPP ABERTO)
# ==============================================================================
def buscar_proximo_lote_ofertas(historico: Set[str]) -> List[Product]:
    """
    Varre as 4 lojas de forma sequencial limpa no thread principal.
    Como o WhatsApp NÃO está aberto neste momento, não há nenhum conflito
    de 'Playwright Sync API inside the asyncio loop'.
    """
    print("\n" + "=" * 70)
    print("  🐾 GARIMPANDO NOVAS OFERTAS NAS 4 LOJAS (SEM LIMITE) 🐾")
    print(f"  Histórico: {len(historico)} produtos já postados hoje")
    print("=" * 70)

    termo_ml = random.choice(TERMOS_MERCADOLIVRE)
    termo_amz = random.choice(TERMOS_AMAZON)
    termo_ali = random.choice(TERMOS_ALIEXPRESS)
    termo_shp = random.choice(TERMOS_SHOPEE)

    raw_products: List[Product] = []

    # 1. Mercado Livre
    print(f"\n[1/4] 🛒 Varrendo Mercado Livre: '{termo_ml}'...")
    try:
        ml = MercadoLivreScraper(headless=False)
        items = ml.search(termo_ml, max_items=12)
        print(f"      [✔] ML: {len(items)} itens coletados")
        raw_products.extend(items)
    except Exception as e:
        print(f"      [!] ML: {e}")

    # 2. Amazon
    print(f"[2/4] 📦 Varrendo Amazon Prime: '{termo_amz}'...")
    try:
        amz = AmazonScraper(headless=True)
        items = amz.search(termo_amz, max_items=12)
        print(f"      [✔] Amazon: {len(items)} itens coletados")
        raw_products.extend(items)
    except Exception as e:
        print(f"      [!] Amazon: {e}")

    # 3. AliExpress
    print(f"[3/4] ✈️ Varrendo AliExpress Choice: '{termo_ali}'...")
    try:
        ali = SafeAliExpressScraper(headless=True)
        items = ali.search(termo_ali, max_items=12)
        print(f"      [✔] AliExpress: {len(items)} itens coletados")
        raw_products.extend(items)
    except Exception as e:
        print(f"      [!] AliExpress: {e}")

    # 4. Shopee
    print(f"[4/4] 🛍️ Varrendo Shopee Brasil: '{termo_shp}'...")
    try:
        shp = SafeShopeeScraper(headless=True)
        items = shp.search(termo_shp, max_items=12)
        print(f"      [✔] Shopee: {len(items)} itens coletados")
        raw_products.extend(items)
    except Exception as e:
        print(f"      [!] Shopee: {e}")

    # Normalização de atributos para todos os produtos coletados
    for p in raw_products:
        normalizar_produto(p)

    # Filtragem Pet + Remoção de já enviados
    validos: List[Product] = []
    for p in deduplicate_products(raw_products):
        normalizar_produto(p)
        if not validar_produto_pet(p):
            continue
        uid = extrair_id_unico(p)
        if uid in historico:
            continue
        
        price = get_preco_produto(p)
        # Aceita produtos na faixa de preço válida de Banho & Tosa
        if 4.0 <= price <= 25000.0:
            validos.append(p)

    validos = aplicar_links_afiliados_robusto(validos)
    print(f"\n[✔] {len(validos)} Novas Ofertas Inéditas Qualificadas encontradas nesta varredura!")
    return validos

def balancear_lote_por_loja(candidatos: List[Product], max_por_rodada: int = 4) -> List[Product]:
    """Garante que a rodada envie um mix diversificado das 4 lojas sem perder produtos."""
    if not candidatos:
        return []

    por_loja = {"shopee": [], "mercadolivre": [], "amazon": [], "aliexpress": [], "outros": []}
    for p in candidatos:
        chave = normalizar_loja(getattr(p, "store", ""))
        por_loja.setdefault(chave, []).append(p)

    # Ordena as listas internas de cada loja: maior desconto primeiro
    for st_list in por_loja.values():
        st_list.sort(key=lambda x: (getattr(x, "discount_percent", 0) or 0), reverse=True)

    selecionados: List[Product] = []

    # 1. Pega 1 produto de cada uma das 4 lojas prioritárias se disponível
    for st_name in ["mercadolivre", "amazon", "shopee", "aliexpress"]:
        if por_loja.get(st_name):
            selecionados.append(por_loja[st_name].pop(0))

    # 2. Se sobrou vaga no lote, completa com as de maior desconto geral
    sobras = [p for lista in por_loja.values() for p in lista]
    sobras.sort(key=lambda x: (getattr(x, "discount_percent", 0) or 0), reverse=True)
    while len(selecionados) < max_por_rodada and sobras:
        selecionados.append(sobras.pop(0))

    return selecionados[:max_por_rodada]

# ==============================================================================
# POSTAGEM FURTIVA (STEALTH) NO WHATSAPP
# ==============================================================================
def enviar_com_cuidado_humano(page: Page, deal: Product, caption: str) -> bool:
    """
    Envia com comportamento 100% humano para passar despercebido:
    - Digitação ritmada com micro-pausas
    - Upload suave de foto real
    - Pausa antes do Enter
    """
    try:
        dialog = page.locator("div[role='dialog']").first
        if dialog.count() > 0 and dialog.is_visible():
            page.keyboard.press("Escape")
            time.sleep(random.uniform(0.5, 1.2))

        # 1. TENTA ENVIAR COM FOTO REAL
        img_path = None
        if getattr(deal, "image_url", None) and deal.image_url.startswith("http"):
            img_path = MediaManager.download_product_image(deal.image_url)

        if img_path and img_path.exists():
            try:
                attach_btn = None
                for sel in (
                    "span[data-icon='plus']", "span[data-icon='attach-menu-plus']",
                    "button[title*='Anexar' i]", "div[title*='Anexar' i]", "[data-testid='clip']"
                ):
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        attach_btn = loc
                        break

                if attach_btn:
                    time.sleep(random.uniform(1.0, 2.0))
                    attach_btn.click()
                    time.sleep(random.uniform(1.0, 1.8))

                    with page.expect_file_chooser(timeout=9000) as fc_info:
                        photo_opt = page.locator("input[type='file'][accept*='image']").first
                        if photo_opt.count() == 0:
                            photo_opt = page.locator("text=/Fotos e vídeos/i").first
                        photo_opt.click()

                    file_chooser = fc_info.value
                    file_chooser.set_files(str(img_path))
                    time.sleep(random.uniform(2.5, 4.0))

                    caption_box = page.locator("div[contenteditable='true'][role='textbox']").last
                    caption_box.wait_for(state="visible", timeout=12000)
                    caption_box.focus()

                    lines = caption.split("\n")
                    for l_idx, line in enumerate(lines):
                        if line:
                            caption_box.type(line, delay=random.randint(4, 12))
                        if l_idx < len(lines) - 1:
                            page.keyboard.press("Shift+Enter")
                            time.sleep(random.uniform(0.1, 0.3))

                    time.sleep(random.uniform(2.5, 4.5))
                    page.keyboard.press("Enter")
                    time.sleep(random.uniform(3.5, 6.0))
                    print("      [✔] Oferta postada com foto real e legenda!")
                    return True
            except Exception as img_err:
                print(f"      [!] Anexo de foto falhou ({img_err}). Usando preview de link...")

        # 2. ENVIO VIA CAIXA DE TEXTO COM PREVIEW DO LINK
        chat_box = page.locator("footer div[contenteditable='true']").first
        chat_box.wait_for(state="visible", timeout=15000)
        chat_box.focus()

        lines = caption.split("\n")
        for l_idx, line in enumerate(lines):
            if line:
                chat_box.type(line, delay=random.randint(4, 10))
            if l_idx < len(lines) - 1:
                page.keyboard.press("Shift+Enter")
                time.sleep(random.uniform(0.1, 0.25))

        tempo_preview = random.uniform(6.0, 8.5)
        print(f"      ⏳ Aguardando prévia de link ({tempo_preview:.1f}s)...")
        time.sleep(tempo_preview)

        page.keyboard.press("Enter")
        time.sleep(random.uniform(3.0, 5.0))
        print("      [✔] Mensagem de oferta enviada com sucesso!")
        return True

    except Exception as e:
        print(f"      [!] Erro no envio: {e}")
        return False

# ==============================================================================
# DISPARADOR DO LOTE NO WHATSAPP COM PROTEÇÃO ANTI-BAN
# ==============================================================================
def enviar_lote_whatsapp(lote: List[Product], historico: Set[str], rodada_num: int) -> int:
    if not lote:
        print("[!] Lote vazio. Operação no WhatsApp cancelada.")
        return 0

    grupo = getattr(config, "DEFAULT_WHATSAPP_GROUP", "Achadinhos banho & tosa 🐶")
    print(f"\n📲 Abrindo WhatsApp Web no grupo '{grupo}' para envio de {len(lote)} oferta(s)...")
    sender = WhatsAppSender()
    enviados_com_sucesso = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(sender.profile_dir),
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-default-browser-check"
            ],
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        try:
            page.wait_for_selector("div#pane-side, div[role='textbox']", timeout=60000)
        except Exception:
            print("[!] WhatsApp Web demorou a carregar. Verifique o QR Code ou a conexão.")
            context.close()
            return 0

        if not sender.open_group_chat(page, grupo):
            print(f"[!] Não foi possível abrir o grupo '{grupo}'.")
            context.close()
            return 0

        for idx, deal in enumerate(lote, start=1):
            normalizar_produto(deal)
            uid = extrair_id_unico(deal)
            hora_atual = datetime.now().strftime("%H:%M:%S")
            loja_nome = deal.store.upper()
            preco_formatado = get_preco_produto(deal)
            disc_formatado = getattr(deal, "discount_percent", 0.0) or 0.0

            print(f"\n[{hora_atual}] 📢 Postando Oferta [{idx}/{len(lote)}] [{loja_nome}]")
            print(f"      📌 {deal.title[:55]}...")
            print(f"      💰 R$ {preco_formatado:.2f} ({disc_formatado:.0f}% OFF)")

            caption = format_single_deal_message(deal, idx, len(lote))
            ok = enviar_com_cuidado_humano(page, deal, caption)

            if ok:
                enviados_com_sucesso += 1
                historico.add(uid)
                salvar_historico(historico)

            # Se ainda restam itens neste lote, aguarda intervalo furtivo humano
            if idx < len(lote):
                minutos_espera = random.uniform(11.0, 16.0)
                segundos_espera = int(minutos_espera * 60)
                proximo_envio = datetime.now() + timedelta(seconds=segundos_espera)
                print(f"\n   💤 [MODO FURTIVO] Intervalo anti-ban: Próxima oferta às {proximo_envio.strftime('%H:%M:%S')} (~{minutos_espera:.1f} min)...")

                while segundos_espera > 0:
                    step = min(60, segundos_espera)
                    time.sleep(step)
                    segundos_espera -= step
                    if segundos_espera > 0 and segundos_espera % 180 == 0:
                        print(f"      ⏳ Faltam {segundos_espera // 60} minuto(s) para a próxima oferta...")

        time.sleep(5)
        context.close()
        print(f"\n[✔] Lote #{rodada_num} finalizado no WhatsApp com {enviados_com_sucesso} ofertas entregues!")
        return enviados_com_sucesso

# ==============================================================================
# MOTOR PRINCIPAL CONTÍNUO (SEM LIMITE + ZERO CONFLITO PLAYWRIGHT)
# ==============================================================================
def executar_cacador_continuo():
    print("\n" + "=" * 75)
    print("      🛡️ PROMOPET HUNTER - MODO FURTIVO CONTÍNUO (SEM LIMITE) 🛡️")
    print("      Operação Orgânica o Dia Todo nas 4 Maiores Plataformas:")
    print("      🛒 Mercado Livre | 📦 Amazon | ✈️ AliExpress | 🛍️ Shopee")
    print("      Proteção Anti-Ban: Intervalos Humanos, Digitação Real e Pausas")
    print("=" * 75)

    historico = carregar_historico()
    rodada = 1

    while True:
        print(f"\n" + "#" * 70)
        print(f"   🚀 INICIANDO RODADA #{rodada} DE GARIMPO (4 LOJAS)")
        print(f"   Total de ofertas já postadas hoje: {len(historico)}")
        print("#" * 70)

        # 1. GARIMPA AS 4 LOJAS COM BROWSER DO WHATSAPP FECHADO (ZERO CONFLITO)
        todas_ofertas = buscar_proximo_lote_ofertas(historico)

        if not todas_ofertas:
            print("\n💤 Nenhuma nova oferta qualificada no momento. Aguardando 3 minutos para nova varredura...")
            time.sleep(3 * 60)
            continue

        # 2. BALANCEIA O LOTE PARA TER VARIEDADE DE LOJAS (3 a 4 OFERTAS POR LOTE)
        lote_selecionado = balancear_lote_por_loja(todas_ofertas, max_por_rodada=4)

        # Se por qualquer motivo não houver itens selecionados, NÃO abre o WhatsApp
        if not lote_selecionado:
            print("\n💤 Nenhum produto restante para este lote. Aguardando 3 minutos...")
            time.sleep(3 * 60)
            continue

        print(f"\n🎯 {len(lote_selecionado)} Super Ofertas Selecionadas para este Lote:")
        for idx, item in enumerate(lote_selecionado, 1):
            normalizar_produto(item)
            preco_item = get_preco_produto(item)
            disc_item = getattr(item, "discount_percent", 0.0) or 0.0
            print(f"   [{idx}] {item.store.upper():<12} | R$ {preco_item:>6.2f} ({disc_item:>2.0f}% OFF) | {item.title[:45]}...")

        # 3. ABRE O WHATSAPP E POSTA COM ESPAÇAMENTO ORGÂNICO ANTI-BAN
        enviadas = enviar_lote_whatsapp(lote_selecionado, historico, rodada)

        # 4. PAUSA NATURAL DE DESCANSO ENTRE RODADAS (SIMULA COMPORTAMENTO HUMANO)
        pausa_minutos = random.uniform(22.0, 32.0)
        previsao_volta = datetime.now() + timedelta(minutes=pausa_minutos)
        print(f"\n☕ [MODO FURTIVO] Rodada #{rodada} concluída!")
        print(f"   Pausa natural de descanso anti-ban: {pausa_minutos:.0f} minutos.")
        print(f"   Próxima rodada de garimpo começará às {previsao_volta.strftime('%H:%M:%S')}...")

        time.sleep(pausa_minutos * 60)
        rodada += 1

if __name__ == "__main__":
    try:
        executar_cacador_continuo()
    except KeyboardInterrupt:
        print("\n\n[🛑] PromoPet Hunter pausado pelo usuário. Histórico preservado com segurança!")
