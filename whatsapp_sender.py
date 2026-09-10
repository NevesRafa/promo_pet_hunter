import random
import re
import time
from pathlib import Path
from typing import List, Optional
from playwright.sync_api import sync_playwright, Page
import config
from scrapers.base import Product
from media_manager import MediaManager

class WhatsAppSender:
    def __init__(self, profile_dir: Path = config.WHATSAPP_PROFILE_DIR):
        self.profile_dir = profile_dir
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def setup_session(self):
        print("'\n" + "=" * 70)
        print("  📲 AUTENTICAÇO DO WHATSAPP WEB")
        print("=" * 70)
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            page.goto("https://web.whatsapp.com")
            try:
                page.wait_for_selector("div#pane-side, div[role='textbox']", timeout=120000)
                print("\n[✔] Login salvo com sucesso!")
                time.sleep(3)
            except Exception:
                print("\n[!] Tempo esgotado para QR Code.")
            context.close()

    def open_group_chat(self, page: Page, group_name: str) -> bool:
        print(f"    🔔 Buscando grupo: '{group_name}'...")
        clean_search = re.sub(r"[^\w\sÀ-ÿ&-]", "", group_name).strip()

        try:
            search_box = None
            for sel in [
                "dif[contenteditable='true'][data-tab='3']",
                "div[role='textbox'][title*='Pesquisar']",
                "dif[contenteditable='true']",
            ]:
                candidate = page.locator(sel).first
                if candidate.is_visible():
                    search_box = candidate
                    break

            if not search_box:
                search_box = page.get_by_placeholder(re.compile("Pesquisar", re.IGNORECASE)).first

            search_box.click()
            time.sleep(0.5)

            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            time.sleep(0.3)

            search_box.type(clean_search, delay=35)
            time.sleep(2.0)

            # Pressiona Enter para abrir o grupo
            page.keyboard.press("Enter")
            time.sleep(2.0)

            msg_box = page.locator("footer div[contenteditable='true']").first
            if msg_box.is_visible():
                print(f"    [✔] Grupo '{group_name}' aberto com sucesso!")
                return True

            list_item = page.locator("div[role='listitem']").filter(
                has_text=re.compile("Achadinhos", re.IGNORECASE)
            ).first
            if list_item.is_visible():
                list_item.click()
                time.sleep(2.0)
                print(f"    [✔] Grupo aberto via clique no card!")
                return True

        except Exception as e:
            print(f"    [!] Erro ao abrir grupo: {e}")

        return False

    def send_deal_with_photo_or_text(self, page: Page, product: Product, caption: str) -> bool:
        try:
            existing_dialog = page.locator("div[role='dialog']").first
            if existing_dialog.count() > 0 and existing_dialog.is_visible():
                page.keyboard.press("Escape")
                time.sleep(0.5)

            img_path = None
            if product.image_url:
                img_path = MediaManager.download_product_image(product.image_url)

            if img_path and img_path.exists():
                print(f"    📺 Anexando foto do produto: {img_path.name}...")
                try:
                    attach_btn = page.locator(
                        "button[title*='Anexar'`i], span[data-icon='plus'], span[data-icon='attach-menu-plus']"
                    ).first
                    attach_btn.wait_for(state="visible", timeout=5000)
                    attach_btn.click()
                    time.sleep(1.0)

                    with page.expect_file_chooser(timeout=7000) as fc_info:
                        photo_opt = page.locator(
                            "input[type='file'][accept*='image'], text=/Fotos e vídeos/i"
                        ).first
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
                            caption_box.type(line, delay=random.randint(4, 12))
                        if l_idx < len(lines) - 1:
                            page.keyboard.press("Shift+Enter")

                    time.sleep(1.5)
                    page.keyboard.press("Enter")
                    time.sleep(4.0)
                    print("    [✔] Oferta postada COM FOTO e LEGENDA")
                    return True
                except Exception as img_err:
                    print(f"    [!] Erro foto ({img_err}). Enviando como texto...")

            chat_box = page.locator("footer div[contenteditable='true']").first
            chat_box.wait_for(state="visible", timeout=15000)
            chat_box.focus()

            lines = caption.split("\n")
            for l_idx, line in enumerate(lines):
                if line:
                    chat_box.type(line, delay=random.randint(4, 12))
                if l_idx < len(lines) - 1:
                    page.keyboard.press("Shift+Enter")

            time.sleep(4.5)
            page.keyboard.press("Enter")
            time.sleep(3.0)
            print("    [✔] Mensagem de texto enviada com sucesso!")
            return True

        except Exception as e:
            print(f"    [!] Falha envio mensagem: {e}")
            return False

    def post_deal_to_group(
        self,
        product: Product,
        caption: str,
        group_name: str = config.DEFAULT_WHATSAPP_GROUP
    ) -> bool:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            page.set_default_timeout(60000)

            print("\n[*] Abrindo WhatsApp Web...")
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

            try:
                page.wait_for_selector("div#pane-side, div[role='textbox']", timeout=50000)
            except Exception:
                print("[!] WhatsApp Web não carregou a tempo.")
                context.close()
                return False

            if not self.open_group_chat(page, group_name):
                print(f"[!] Não conseguiu abrir o grupo '{group_name}'.")
                context.close()
                return False

            success = self.send_deal_with_photo_or_text(page, product, caption)
            time.sleep(2.5)
            context.close()
            return success
