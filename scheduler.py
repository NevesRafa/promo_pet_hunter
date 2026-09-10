import argparse
import random
import sys
import time
from datetime import datetime, timedelta
from typing import List, Optional

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

class DealScheduler:
    def __init__(
        self,
        group_name: str = config.DEFAULT_WHATSAPP_GROUP,
        start_hour: int = config.START_HOUR,
        end_hour: int = config.END_HOUR,
        min_interval_mins: float = config.MIN_INTERVAL_MINUTES,
        max_interval_mins: float = config.MAX_INTERVAL_MINUTES
    ):
        self.group_name = group_name
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.min_interval_mins = min_interval_mins
        self.max_interval_mins = max_interval_mins
        self.sender = WhatsAppSender()

    def is_within_window(self) -> bool:
        now = datetime.now()
        return self.start_hour <= now.hour < self.end_hour

    def seconds_until_next_start(self) -> float:
        now = datetime.now()
        target = now.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        if now.hour >= self.end_hour or (now.hour == self.start_hour and now.minute > 0):
            target += timedelta(days=1)
        return max(10.0, (target - now).total_seconds())

    def fetch_top_deals(self, count: int = 10, stores: Optional[List[str]] = None) -> List[Product]:
        if stores is None:
            stores = ["mercadolivre", "amazon"]

        stores_clean = [s.lower() for s in stores]
        print("\n" + "=" * 70)
        print(f"  🐾 VARRENDO OFERTAS PET: [{', '.join(stores_clean).upper()}] 🐾")
        print("=" * 70)
        all_products: List[Product] = []

        if "mercadolivre" in stores_clean:
            print("[+] Varrendo Mercado Livre...")
            try:
                ml = MercadoLivreScraper(headless=False)
                for term in config.DEFAULT_SEARCH_TERMS[:2]:
                    items = ml.search(term, max_items=20)
                    all_products.extend(items)
            except Exception as e:
                print(f"    [!] Erro no ML: {e}")

        if "amazon" in stores_clean:
            print("[+] Varrendo Amazon (Stealth)...")
            try:
                amz = AmazonScraper(headless=True)
                for term in config.DEFAULT_SEARCH_TERMS[:2]:
                    items = amz.search(term, max_items=20)
                    all_products.extend(items)
            except Exception as e:
                print(f"    [!] Erro na Amazon: {e}")

        unique_items = deduplicate_products(all_products)
        filtered = apply_filters(unique_items, require_discount=True)

        if len(filtered) < count:
            remaining = [p for p in unique_items if p not in filtered]
            remaining.sort(key=lambda x: (x.rating, x.discount_percent), reverse=True)
            filtered.extend(remaining[:(count - len(filtered))])

        top_deals = filtered[:count]
        top_deals = apply_affiliate_links(top_deals)
        print(f"[✔] {len(top_deals)} Melhores Ofertas Selecionadas!")
        return top_deals

    def run_single_test(self, target_store: Optional[str] = None):
        lojas = [target_store] if target_store else ["amazon"]
        print(f"\n[*] Modo Teste: Buscando 1 oferta na loja: {', '.join(lojas).upper()}...")
        deals = self.fetch_top_deals(count=1, stores=lojas)

        if not deals:
            print(f"[!] Buscando produtos populares na Amazon...")
            all_amz = []
            amz = AmazonScraper(headless=True)
            for term in config.DEFAULT_SEARCH_TERMS[:2]:
                all_amz.extend(amz.search(term, max_items=15))
            if all_amz:
                all_amz.sort(key=lambda x: x.rating, reverse=True)
                deals = apply_affiliate_links([all_amz[0]])

        if not deals:
            print("[!] Não foi possível encontrar produtos na Amazon.")
            return

        deal = deals[0]
        caption = format_single_deal_message(deal, 1, 1)
        print(f"\n[*] Postando oferta da [{deal.store}] no grupo '{self.group_name}'...")
        success = self.sender.post_deal_to_group(deal, caption, group_name=self.group_name)
        if success:
            print(f"[✔] Oferta enviada com sucesso no grupo '{self.group_name}'!")
        else:
            print("[!] Falha no envio da oferta.")

    def start_day_schedule(self):
        print("\n" + "=" * 70)
        print("  🕒 AGENDADOR DE OFERTAS: MERCADO LIVRE & AMAZON")
        print(f"  Horário: {self.start_hour:02d}:00 até {self.end_hour:02d}:00")
        print(f"  Intervalo: {self.min_interval_mins:.0f} a {self.max_interval_mins:.0f} minutos")
        print("=" * 70)

        while True:
            now = datetime.now()
            if not self.is_within_window():
                wait_sec = self.seconds_until_next_start()
                resume_time = now + timedelta(seconds=wait_sec)
                print(f"\n[🌙] Fora do horário comercial. Aguardando até {resume_time.strftime('%d/%m às %H:%M')}...")
                time.sleep(wait_sec)
                continue

            deals = self.fetch_top_deals(count=10)
            if not deals:
                print("[!] Nenhuma oferta aprovada hoje. Tentando em 1 hora...")
                time.sleep(3600)
                continue

            total = len(deals)
            for i, deal in enumerate(deals, 1):
                if not self.is_within_window():
                    break

                caption = format_single_deal_message(deal, i, total)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📢 Postando [{i}/{total}] [{deal.store}] no grupo '{self.group_name}'...")
                self.sender.post_deal_to_group(deal, caption, group_name=self.group_name)

                if i < total and self.is_within_window():
                    interval_min = random.uniform(self.min_interval_mins, self.max_interval_mins)
                    next_post = datetime.now() + timedelta(minutes=interval_min)
                    print(f"    ⏳ Pausa de {interval_min:.1f} minutos...")
                    time.sleep(interval_min * 60)

            wait_night = self.seconds_until_next_start()
            print(f"    Dormindo até amanhã às {self.start_hour}:00...")
            time.sleep(wait_night)
