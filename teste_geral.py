import random
import sys
import time
from pathlib import Path
from typing import List

# Suporte UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import config
from scrapers.base import Product
from scrapers.mercadolivre import MercadoLivreScraper
from scrapers.amazon import AmazonScraper
from filters import apply_filters, deduplicate_products
from affiliate import apply_affiliate_links
from templates import format_single_deal_message
from whatsapp_sender import WhatsAppSender
from media_manager import MediaManager
from playwright.sync_api import sync_playwright, Page

def banner():
    print("=" * 70)
    print("  🚀 TESTE GERAL: MERCADO LIVRE & AMAZON -> WHATSAPP")
    print("     Buscando as melhores ofertas pet e enviando de uma vez")
    print("=" * 70)

def search_best_deals() -> List[Product]:
    all_ml: List[Product] = []
    all_amz: List[Product] = []

    # 1. Busca no Mercado Livre
    print("\n[1/4] 🛒 Varrendo Mercado Livre...")
    try:
        ml = MercadoLivreScraper(headless=False)
        for term in config.DEFAULT_SEARCH_TERMS[:2]:
            print(f"      🔎 Buscando ML: '{term}'...")
            items = ml.search(term, max_items=15)
            all_ml.extend(items)
    except Exception as e:
        print(f"      [!] Erro no Mercado Livre: {e}")

    # 2. Busca na Amazon
    print("\n[2/4] 📦 Varrendo Amazon (Stealth)...")
    try:
        amz = AmazonScraper(headless=True)
        for term in config.DEFAULT_SEARCH_TERMS[:2]:
            print(f"      🔎 Buscando Amazon: '{term}'...")
            items = amz.search(term, max_items=15)
            all_amz.extend(items)
    except Exception as e:
        print(f"      [!] Erro na Amazon: {e}")

    # 3. Filtra e seleciona as melhores de cada
    print("\n[3/4] 🎯 Filtrando e rankeando as melhores promoções...")
    
    # Melhores do Mercado Livre
    ml_unique = deduplicate_products(all_ml)
    ml_filtered = apply_filters(ml_unique, require_discount=True)
    if len(ml_filtered) < 2:
        remaining = [p for p in ml_unique if p not in ml_filtered]
        remaining.sort(key=lambda x: (getattr(x, 'rating', 0), getattr(x, 'discount_percent', 0)), reverse=True)
        ml_filtered.extend(remaining[:2 - len(ml_filtered)])
    top_ml = ml_filtered[:2]

    # Melhores da Amazon
    amz_unique = deduplicate_products(all_amz)
    amz_filtered = apply_filters(amz_unique, require_discount=True)
    if len(amz_filtered) < 2:
        remaining = [p for p in amz_unique if p not in amz_filtered]
        remaining.sort(key=lambda x: (getattr(x, 'rating', 0), getattr(x, 'discount_percent', 0)), reverse=True)
        amz_filtered.extend(remaining[:2 - len(amz_filtered)])
    top_amz = amz_filtered[:2]

    # Junta as melhores ofertas
    selected_deals = top_ml + top_amz
    selected_deals = apply_affiliate_links(selected_deals)

    print(f"\n[✔] Total selecionado: {len(selected_deals)} ofertas:")
    for idx, d in enumerate(selected_deals, 1):
        price_val = getattr(d, 'price', getattr(d, 'current_price', getattr(d, 'promo_price', '')))
        price_str = f"R$ {price_val:.2f}" if isinstance(price_val, (int, float)) else str(price_val)
        disc_val = getattr(d, 'discount_percent', 0)
        print(f"    {idx}. [{d.store.upper()}] {d.title[:45]}... | {price_str} ({disc_val:.0f}% OFF)")
        print(f"       Link: {d.url}")

    return selected_deals

def send_deal(page: Page, product: Product, caption: str) -> bool:
    try:
        existing_dialog = page.locator("div[role='dialog']").first
        if existing_dialog.count() > 0 and existing_dialog.is_visible():
            page.keyboard.press("Escape")
            time.sleep(0.5)

        img_path = None
        if getattr(product, 'image_url', None):
            img_path = MediaManager.download_product_image(product.image_url)

        if img_path and img_path.exists():
            print(f"      📸 Anexando foto: {img_path.name}...")
            try:
                # Seletor robusto e compatível para o botão de anexo do WhatsApp
                attach_btn = None
                selectors = [
                    "span[data-icon='plus']",
                    "span[data-icon='attach-menu-plus']",
                    "button[title*='Anexar']",
                    "div[title*='Anexar']",
                    "[data-testid='clip']",
                    "[data-testid='attach-menu-plus']",
                ]
                for sel in selectors:
                    loc = page.locator(sel).first
                    if loc.count() > 0:
                        attach_btn = loc
                        break

                if attach_btn:
                    attach_btn.click()
                    time.sleep(1.0)
                    with page.expect_file_chooser(timeout=7000) as fc_info:
                        photo_opt = page.locator("input[type='file'][accept*='image']").first
                        if photo_opt.count() == 0:
                            photo_opt = page.locator("text=/Fotos e vídeos/i").first
                        photo_opt.click()
                    file_chooser = fc_info.value
                    file_chooser.set_files(str(img_path))
                    time.sleep(2.5)

                    caption_box = page.locator("div[contenteditable='true'][role='textbox']").last
                    caption_box.wait_for(state="visible", timeout=8000)
                    caption_box.focus()

                    lines = caption.split("\n")
                    for l_idx, line in enumerate(lines):
                        if line:
                            caption_box.type(line, delay=random.randint(3, 8))
                        if l_idx < len(lines) - 1:
                            page.keyboard.press("Shift+Enter")

                    time.sleep(1.5)
                    page.keyboard.press("Enter")
                    time.sleep(4.0)
                    print("      [✔] Oferta enviada com FOTO e LEGENDA!")
                    return True
            except Exception as img_err:
                print(f"      [!] Erro foto ({img_err}). Enviando como texto...")

        # Envio como texto simples caso foto falhe
        chat_box = page.locator("footer div[contenteditable='true']").first
        chat_box.wait_for(state="visible", timeout=12000)
        chat_box.focus()

        lines = caption.split("\n")
        for l_idx, line in enumerate(lines):
            if line:
                chat_box.type(line, delay=random.randint(3, 8))
            if l_idx < len(lines) - 1:
                page.keyboard.press("Shift+Enter")

        time.sleep(2.0)
        page.keyboard.press("Enter")
        time.sleep(3.0)
        print("      [✔] Mensagem de texto enviada!")
        return True

    except Exception as e:
        print(f"      [!] Falha no envio: {e}")
        return False

def dispatch_all_to_whatsapp(deals: List[Product]):
    group_name = config.DEFAULT_WHATSAPP_GROUP
    print(f"\n[4/4] 📲 Abrindo WhatsApp Web e postando no grupo '{group_name}'...")

    sender = WhatsAppSender()
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(sender.profile_dir),
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        page.set_default_timeout(60000)

        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
        try:
            page.wait_for_selector("div#pane-side, div[role='textbox']", timeout=50000)
        except Exception:
            print("[!] WhatsApp Web não carregou a tempo.")
            context.close()
            return

        if not sender.open_group_chat(page, group_name):
            print(f"[!] Não foi possível abrir o grupo '{group_name}'.")
            context.close()
            return

        total = len(deals)
        for i, deal in enumerate(deals, 1):
            caption = format_single_deal_message(deal, i, total)
            print(f"\n  📢 Postando [{i}/{total}] [{deal.store.upper()}] no grupo...")
            send_deal(page, deal, caption)
            if i < total:
                wait_sec = random.uniform(4, 7)
                print(f"     ⏳ Aguardando {wait_sec:.1f}s antes da próxima...")
                time.sleep(wait_sec)

        print(f"\n[✔] Todas as {total} ofertas foram enviadas com sucesso no grupo!")
        time.sleep(3.0)
        context.close()

if __name__ == "__main__":
    banner()
    deals = search_best_deals()
    if not deals:
        print("[!] Nenhuma oferta encontrada para envio.")
        sys.exit(1)
    dispatch_all_to_whatsapp(deals)
