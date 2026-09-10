import argparse
import sys
from typing import List

# Garante suporte a UTF-8 no terminal Windows
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
from exporters import Exporter
from templates import format_deals_as_separate_messages, format_top10_whatsapp_message, build_wa_me_link
from whatsapp_sender import WhatsAppSender

def run_daily_pipeline(
    terms: List[str] = config.DEFAULT_SEARCH_TERMS,
    send_whatsapp: bool = True,
    phone: str = config.DEFAULT_WHATSAPP_PHONE,
    separate_messages: bool = True
):
    print("""
========================================================================
   🐾 PROMO-PET HUNTER - Pipeline Diário de Ofertas & Afiliados 🐾
========================================================================
    """)
    print(f"[*] Termos a varrer: {len(terms)}")
    print(f"[*] Destinatário WhatsApp: +{phone}")
    print(f"[*] Formato de envio: {'Mensagens Separadas (1 card por oferta)' if separate_messages else 'Mensagem Única Consolidada'}")
    print(f"[*] Afiliado Amazon: {config.AMAZON_TAG}")
    print(f"[*] Afiliado Mercado Livre: {config.MELI_MATT_TOOL} ({config.MELI_MATT_WORD})\n")

    all_products: List[Product] = []

    # 1. Mercado Livre
    print("[+] Varrendo Mercado Livre...")
    ml = MercadoLivreScraper(headless=False)
    for term in terms:
        print(f"    🔍 [ML] '{term}'...")
        items = ml.search(term, max_items=25)
        all_products.extend(items)

    # 2. Amazon
    print("\n[+] Varrendo Amazon (Stealth)...")
    amz = AmazonScraper(headless=True)
    for term in terms:
        print(f"    🔍 [Amazon] '{term}'...")
        items = amz.search(term, max_items=25)
        all_products.extend(items)

    # 3. Deduplicação e Filtros
    print(f"\n[*] Total bruto coletado: {len(all_products)}")
    unique_items = deduplicate_products(all_products)
    
    # Aplica filtros de qualidade
    filtered = apply_filters(
        unique_items,
        min_rating=config.MIN_RATING,
        min_reviews=config.MIN_REVIEWS,
        min_discount=config.MIN_DISCOUNT_PERCENT,
        require_discount=True
    )

    # Complementa para garantir 10 ofertas se necessário
    if len(filtered) < 10:
        remaining = [p for p in unique_items if p not in filtered]
        remaining.sort(key=lambda x: (x.rating, x.discount_percent), reverse=True)
        filtered.extend(remaining[:(10 - len(filtered))])

    top_10 = filtered[:10]
    print(f"[✔] Top {len(top_10)} Melhores Ofertas Selecionadas!")

    # 4. Geração de Links de Afiliado
    print("[*] Aplicando tags de afiliado a todos os produtos...")
    top_10 = apply_affiliate_links(top_10)

    # 5. Exportação para Excel, Bloco de Notas e CSV
    paths = Exporter.export_all(top_10, base_name="top10_afiliados_pet")
    print(f"    📊 Planilha Excel atualizada: {paths['excel']}")
    print(f"    📝 Bloco de Notas atualizado: {paths['txt']}")

    # 6. Formatação das Mensagens
    if separate_messages:
        messages = format_deals_as_separate_messages(top_10)
        print("\n" + "=" * 70)
        print(f"  EXEMPLO DO 1º CARD DE OFERTA (DE UM TOTAL DE {len(messages)})")
        print("=" * 70)
        if messages:
            print(messages[0])
        print("=" * 70)
    else:
        consolidated = format_top10_whatsapp_message(top_10)
        messages = [consolidated]
        print("\n" + "=" * 70)
        print("  MENSAGEM CONSOLIDADA DO WHATSAPP")
        print("=" * 70)
        print(consolidated)
        print("=" * 70)

    # Link wa.me do primeiro item para teste rápido
    if messages:
        print(f"\n🔗 Link direto wa.me do 1º item: {build_wa_me_link(phone, messages[0])}\n")

    # 7. Disparo pelo WhatsApp Web com proteção anti-ban
    if send_whatsapp:
        sender = WhatsAppSender()
        sender.send_multiple_messages(
            messages,
            phone=phone,
            min_delay=config.WHATSAPP_MIN_DELAY_SECS,
            max_delay=config.WHATSAPP_MAX_DELAY_SECS
        )

def main():
    parser = argparse.ArgumentParser(description="Pipeline Diário de Ofertas Pet com Mensagens Separadas e Afiliados")
    parser.add_argument("--terms", nargs="+", default=config.DEFAULT_SEARCH_TERMS[:3], help="Termos de busca")
    parser.add_argument("--no-whatsapp", action="store_true", help="Apenas gera os links e a planilha sem disparar no WhatsApp")
    parser.add_argument("--phone", default=config.DEFAULT_WHATSAPP_PHONE, help="Número do WhatsApp de destino")
    parser.add_argument("--combined", action="store_true", help="Envia todas as ofertas em 1 mensagem única em vez de separadas")
    parser.add_argument("--login-whatsapp", action="store_true", help="Abre o WhatsApp Web para ler o QR Code uma vez")
    args = parser.parse_args()

    if args.login_whatsapp:
        sender = WhatsAppSender()
        sender.setup_session()
        return

    run_daily_pipeline(
        terms=args.terms,
        send_whatsapp=not args.no_whatsapp,
        phone=args.phone,
        separate_messages=not args.combined
    )

if __name__ == "__main__":
    main()
