import random
import urllib.parse
from datetime import datetime
from typing import List
from scrapers.base import Product

_ABRE_CHAMADA = [
    "🚨 *ACHADO DO DIA* 🚨",
    "🔥 *OFERTA RELÂMPAGO* 🔥",
    "🐾 *ACHADINHO BANHO & TOSA* 🐾",
    "⚡ *PROMOÇÃO IMPERDÍVEL* ⚡",
    "🎯 *DESCONTAÇO PRA VOCÊ* 🎯",
]

_CTA_FINAL = [
    "👉 *Corre que costuma esgotar rápido!*",
    "👉 *Aproveita antes que o preço volte ao normal!*",
    "👉 *Estoque limitado, garante o seu!*",
    "👉 *Enquanto durar o preço, é hoje!*",
]

def format_single_deal_message(p: Product, index: int, total: int) -> str:
    """
    Formata um card individual de oferta para o WhatsApp, com linguagem
    chamativa (urgência + destaque de desconto) para gerar mais cliques.
    Ao enviar 1 link por mensagem, o WhatsApp gera o Card com a Foto do
    produto automaticamente.
    """
    curr_str = f"R$ {p.current_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    abertura = random.choice(_ABRE_CHAMADA)

    lines = [
        f"{abertura} [{index}/{total}]",
        f"*{p.title}*",
        ""
    ]

    if p.original_price and p.original_price > p.current_price:
        orig_str = f"~R$ {p.original_price:,.2f}~".replace(",", "X").replace(".", ",").replace("X", ".")
        lines.append(f"💥 De {orig_str} por *{curr_str}*")
        lines.append(f"📉 *-{p.discount_percent:.0f}% DE DESCONTO!*")
    else:
        lines.append(f"💰 Por apenas *{curr_str}*")

    rating_stars = "★" * int(round(p.rating))
    shipping = " | 🚚 _Frete Grátis_" if getattr(p, "free_shipping", False) else ""
    lines.append(f"⭐ *{p.rating:.1f}/5.0* {rating_stars} ({p.reviews_count} avaliações){shipping}")
    lines.append(f"🏪 *Loja:* {p.store}")
    lines.append("")
    lines.append(random.choice(_CTA_FINAL))
    lines.append(p.url)

    return "\n".join(lines)

def format_deals_as_separate_messages(products: List[Product]) -> List[str]:
    """Retorna uma lista contendo uma mensagem formatada para cada produto."""
    total = len(products)
    return [format_single_deal_message(p, i, total) for i, p in enumerate(products, 1)]

def format_top10_whatsapp_message(products: List[Product]) -> str:
    """Gera a mensagem consolidada (todas as ofertas em 1 bloco só)."""
    date_str = datetime.now().strftime("%d/%m/%Y")
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    lines = [
        "🔥 *TOP OFERTAS DE HOJE: BANHO & TOSA* 🐾",
        f"📅 _Atualizado em: {date_str}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]

    for i, p in enumerate(products[:10]):
        emoji_num = number_emojis[i] if i < len(number_emojis) else f"[{i+1}]"
        short_title = p.title[:55] + "..." if len(p.title) > 55 else p.title

        lines.append(f"{emoji_num} *{short_title}*")

        curr_str = f"R$ {p.current_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if p.original_price and p.original_price > p.current_price:
            orig_str = f"~R$ {p.original_price:,.2f}~".replace(",", "X").replace(".", ",").replace("X", ".")
            lines.append(f"💰 *{curr_str}* (De {orig_str}) 📉 *-{p.discount_percent:.0f}% OFF*")
        else:
            lines.append(f"💰 *{curr_str}*")

        rating_stars = "★" * int(round(p.rating))
        shipping_tag = " | 🚚 _Frete Grátis_" if getattr(p, "free_shipping", False) else ""
        lines.append(f"⭐ *{p.rating:.1f}/5.0* {rating_stars} ({p.reviews_count} aval.){shipping_tag}")
        lines.append(f"🏪 *Loja:* {p.store}")
        lines.append(f"👉 *Compre aqui:* {p.url}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("⚡ _Preços e estoques podem mudar a qualquer momento — corre lá!_")

    return "\n".join(lines)

def build_wa_me_link(phone: str, message: str) -> str:
    """Gera um link clicável wa.me pronto para abrir no celular ou navegador."""
    clean_phone = "".join(filter(str.isdigit, phone))
    encoded_text = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_text}"
