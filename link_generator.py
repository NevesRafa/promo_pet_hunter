import re
import time
from typing import Optional
from playwright.sync_api import sync_playwright
import config
from affiliate import build_amazon_affiliate_url, build_mercadolivre_affiliate_url

class LinkGenerator:
    """Gera links normais e diretos de afiliado sem nenhum encurtador de terceiros."""

    @staticmethod
    def _launch_context(p, profile_dir, headless: bool = False):
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            viewport={"width": 1280, "height": 800},
            timeout=30000,
        )
        return context

    @staticmethod
    def get_meli_official_link(product_url: str) -> str:
        return build_mercadolivre_affiliate_url(product_url)

    @staticmethod
    def get_amazon_official_link(product_url: str) -> str:
        return build_amazon_affiliate_url(product_url)
