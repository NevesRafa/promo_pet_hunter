# -*- coding: utf-8 -*-
"""
PromoPet Hunter — Ponto de entrada único do projeto.
Lojas ativas nesta versão: MERCADO LIVRE e AMAZON.

Uso:
    python bot.py                 -> inicia o garimpo contínuo (dentro da janela operacional)
    python bot.py --login-whatsapp -> abre o WhatsApp Web para ler o QR Code uma vez
    python bot.py --test           -> garimpa e posta 1 oferta agora mesmo, pra testar

O que este script garante:
    - Só posta descontos DE VERDADE (>= config.MIN_DISCOUNT_PERCENT).
    - Nunca repete um produto já postado no mesmo dia (historico_enviados.json).
    - Só aceita produtos genuinamente de pet shop / banho & tosa (bloqueia
      resultados de nicho errado como automotivo, cabelo humano, bebê etc.).
    - Comportamento humano no WhatsApp (digitação ritmada, pausas variáveis).
"""

import argparse
import json
import random
import re
import sys
import time
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
from templates import format_single_deal_message, format_top10_whatsapp_message
from whatsapp_sender import WhatsAppSender
from media_manager import MediaManager
from exporters import Exporter
from playwright.sync_api import sync_playwright, Page


# ==============================================================================
# HISTÓRICO LOCAL (ANTI-REPETIÇÃO) — persiste entre execuções, reseta por dia
# ==============================================================================
def carregar_historico() -> Set[str]:
    if not config.HISTORICO_FILE.exists():
        return set()
    try:
        with open(config.HISTORICO_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def salvar_historico(historico: Set[str]):
    try:
        with open(config.HISTORICO_FILE, "w", encoding="utf-8") as f:
            json.dump(list(historico), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f" [!] Erro ao salvar histórico: {e}")

def extrair_id_unico(produto: Product) -> str:
    """ID estável pro histórico — por código do produto, não pela URL toda
    (que pode mudar por causa de parâmetros de rastreamento)."""
    url = produto.url or ""
    m_mlb = re.search(r'(MLB-?\d{8,14})', url, re.IGNORECASE)
    if m_mlb:
        return f"ml_{m_mlb.group(1).upper().replace('-', '')}"
    m_asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url, re.IGNORECASE)
    if m_asin:
        return f"amz_{m_asin.group(1).upper()}"
    return url.split('?')[0].split('#')[0]


# ==============================================================================
# NORMALIZAÇÃO DE PREÇOS (BLINDAGEM — diferentes scrapers usam nomes diferentes)
# ==============================================================================
def get_preco_produto(p) -> float:
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
    preco = get_preco_produto(p)
    for attr, val in (("price", preco), ("current_price", preco)):
        try:
            setattr(p, attr, val)
        except Exception:
            pass
    try:
        p.discount_percent = float(getattr(p, "discount_percent", 0.0) or 0.0)
    except Exception:
        p.discount_percent = 0.0
    try:
        p.rating = float(getattr(p, "rating", 0.0) or 0.0)
    except Exception:
        p.rating = 0.0
    try:
        p.reviews_count = int(getattr(p, "reviews_count", 0) or 0)
    except Exception:
        p.reviews_count = 0
    return p


# ==============================================================================
# LINKS DE AFILIADO OFICIAIS (Mercado Livre e Amazon)
# ==============================================================================
def construir_link_meli(url_original: str) -> str:
    """
    Normaliza qualquer link do Mercado Livre para o formato canônico com tag
    de afiliado, evitando 404: desempacota redirecionamentos de anúncios
    patrocinados, suporta produtos de catálogo (/p/MLB...) e produtos normais,
    e corrige duplicidade acidental de prefixo (MLB-MLB...).
    """
    if not url_original:
        return url_original

    url = url_original.strip()
    tool_id = config.MELI_MATT_TOOL
    word_id = config.MELI_MATT_WORD

    # 1. Anúncio patrocinado (click1.mercadolivre / /mclics/ / redirect)
    if any(k in url.lower() for k in ["click1.", "/mclics/", "click?", "custom_url="]):
        try:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            for param in ["custom_url", "url", "go", "redirect", "target", "link"]:
                if param in qs and qs[param]:
                    target = urllib.parse.unquote(qs[param][0])
                    if "mercadolivre.com" in target:
                        return construir_link_meli(target)
        except Exception:
            pass

    # 2. Produto de catálogo (/p/MLB...)
    p_match = re.search(r'/p/(MLB\d+)', url, re.IGNORECASE)
    if p_match:
        p_code = p_match.group(1).upper()
        clean = url.split('#')[0].split('?')[0].rstrip('/')
        if f"/p/{p_code}" in clean or f"/p/{p_code.lower()}" in clean:
            return f"{clean}?matt_tool={tool_id}&matt_word={word_id}"
        return f"https://www.mercadolivre.com.br/p/{p_code}?matt_tool={tool_id}&matt_word={word_id}"

    # 3. Produto normal com slug e código MLB
    clean = url.split('#')[0].split('?')[0].rstrip('/')
    clean = clean.replace("MLB-MLB", "MLB-")
    if "produto.mercadolivre.com.br/MLB-" in clean:
        return f"{clean}?matt_tool={tool_id}&matt_word={word_id}"

    # 4. Fallback canônico caso a URL venha encurtada/truncada
    num_match = re.search(r'MLB-?(\d{8,14})', url, re.IGNORECASE)
    if num_match:
        num_code = num_match.group(1)
        return f"https://produto.mercadolivre.com.br/MLB-{num_code}?matt_tool={tool_id}&matt_word={word_id}"

    # 5. Fallback geral
    return f"{clean}?matt_tool={tool_id}&matt_word={word_id}"

def construir_link_amazon(url_original: str) -> str:
    """Localiza o ASIN e constrói o link canônico limpo com a tag de afiliado."""
    tag = config.AMAZON_TAG
    asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url_original, re.IGNORECASE)
    if asin_match:
        asin = asin_match.group(1).upper()
        return f"https://www.amazon.com.br/dp/{asin}?tag={tag}"
    url_limpa = url_original.split('#')[0].split('?')[0].strip()
    return f"{url_limpa}?tag={tag}"

def aplicar_links_afiliados(produtos: List[Product]) -> List[Product]:
    for p in produtos:
        store = (p.store or "").lower()
        if "mercado" in store or "meli" in store:
            p.url = construir_link_meli(p.url)
        elif "amazon" in store:
            p.url = construir_link_amazon(p.url)
    return produtos


# ==============================================================================
# VALIDAÇÃO: só passa se for pet/banho-e-tosa de verdade E tiver desconto real
# ==============================================================================
def validar_produto_pet(produto: Product) -> bool:
    titulo = (produto.title or "").lower()
    for termo_proibido in config.PALAVRAS_PROIBIDAS_NAO_PET:
        if re.search(r'\b' + re.escape(termo_proibido) + r'\b', titulo):
            return False
    return any(termo_pet in titulo for termo_pet in config.PALAVRAS_OBRIGATORIAS_PET)

def produto_qualifica(p: Product, historico: Set[str]) -> bool:
    """Checagem única e completa: pet de verdade, não repetido, preço plausível,
    avaliação mínima e DESCONTO REAL (nada de 0% passar como promoção)."""
    if not validar_produto_pet(p):
        return False
    if extrair_id_unico(p) in historico:
        return False
    preco = get_preco_produto(p)
    if not (config.PRECO_MIN <= preco <= config.PRECO_MAX):
        return False
    if (p.rating or 0) < config.MIN_RATING:
        return False
    if (p.reviews_count or 0) < config.MIN_REVIEWS:
        return False
    if (p.discount_percent or 0) < config.MIN_DISCOUNT_PERCENT:
        return False
    return True


# ==============================================================================
# ESTATÍSTICAS DO DIA (pro diagnóstico via WhatsApp)
# ==============================================================================
ESTATISTICAS_DIA = {
    "rodadas": 0,
    "erros_meli": 0,
    "erros_amazon": 0,
    "ultima_postagem_sucesso": None,   # datetime ou None
    "ultimo_diagnostico_enviado": None,  # datetime ou None
}

def resetar_estatisticas_dia():
    ESTATISTICAS_DIA["rodadas"] = 0
    ESTATISTICAS_DIA["erros_meli"] = 0
    ESTATISTICAS_DIA["erros_amazon"] = 0
    ESTATISTICAS_DIA["ultima_postagem_sucesso"] = None
    # Não reseta ultimo_diagnostico_enviado — evita mandar 2 diagnósticos seguidos
    # bem na virada do dia.


# ==============================================================================
# GARIMPO: MERCADO LIVRE + AMAZON
# ==============================================================================
def garimpar_ofertas(
    historico: Set[str],
    lojas: Optional[Set[str]] = None,
) -> List[Product]:
    lojas = lojas or set(config.LOJAS_ATIVAS)

    print("\n" + "=" * 72)
    print(f"  🐾 GARIMPO PET SHOP / BANHO & TOSA: {', '.join(sorted(lojas)).upper()} 🐾")
    print(f"  Itens já enviados hoje: {len(historico)}")
    print("=" * 72)

    raw_items: List[Product] = []

    scrapers = {
        "mercadolivre": (
            "Mercado Livre",
            MercadoLivreScraper,
            config.CATEGORIAS_MERCADOLIVRE,
            False,
        ),
        "amazon": (
            "Amazon",
            AmazonScraper,
            config.CATEGORIAS_AMAZON,
            True,
        ),
    }
    for store_key in ("mercadolivre", "amazon"):
        if store_key not in lojas:
            continue
        store_name, scraper_class, categories, headless = scrapers[store_key]
        category_name = random.choice(list(categories))
        term = random.choice(categories[category_name])
        print(f"\n[{store_name}] categoria '{category_name}': pesquisando '{term}'...")
        try:
            scraper = scraper_class(headless=headless)
            items = scraper.search(term, max_items=15)
            print(f"      [✔] {len(items)} produtos encontrados na {store_name}")
            raw_items.extend(items)
        except Exception as e:
            print(f"      [!] Erro na {store_name}: {e}")
            stat_key = "erros_meli" if store_key == "mercadolivre" else f"erros_{store_key}"
            ESTATISTICAS_DIA[stat_key] += 1

    validos: List[Product] = []
    for p in deduplicate_products(raw_items):
        normalizar_produto(p)
        if produto_qualifica(p, historico):
            validos.append(p)

    validos = aplicar_links_afiliados(validos)
    print(f"\n[✔] {len(validos)} ofertas novas, inéditas e com desconto real!")
    return validos

def montar_lote_equilibrado(candidatos: List[Product], max_items: int) -> List[Product]:
    """Alterna entre as lojas disponíveis, priorizando desconto e avaliação."""
    if not candidatos:
        return []

    meli = [p for p in candidatos if "mercado" in (p.store or "").lower()]
    amz = [p for p in candidatos if "amazon" in (p.store or "").lower()]

    meli.sort(key=lambda x: (x.discount_percent or 0, x.rating or 0), reverse=True)
    amz.sort(key=lambda x: (x.discount_percent or 0, x.rating or 0), reverse=True)

    lote: List[Product] = []
    filas = [meli, amz]
    while len(lote) < max_items and any(filas):
        for fila in filas:
            if fila and len(lote) < max_items:
                lote.append(fila.pop(0))
    return lote


# ==============================================================================
# POSTAGEM HUMANA NO WHATSAPP (ANTI-BAN)
# ==============================================================================
def postar_com_comportamento_humano(page: Page, deal: Product, caption: str) -> bool:
    try:
        img_path = None
        if getattr(deal, "image_url", None) and deal.image_url.startswith("http"):
            img_path = MediaManager.download_product_image(deal.image_url)
            if not img_path:
                print("      ℹ️ Não deu pra baixar a foto real — vai tentar a prévia de link.")
        else:
            print("      ℹ️ Produto sem image_url válida — vai tentar a prévia de link.")

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
                    time.sleep(random.uniform(1.2, 2.2))
                    attach_btn.click()
                    time.sleep(random.uniform(1.0, 1.8))

                    with page.expect_file_chooser(timeout=9000) as fc_info:
                        photo_opt = page.locator("input[type='file'][accept*='image']").first
                        if photo_opt.count() == 0:
                            photo_opt = page.locator("text=/Fotos e vídeos/i").first
                        photo_opt.click()

                    fc = fc_info.value
                    fc.set_files(str(img_path))
                    time.sleep(random.uniform(2.5, 4.0))

                    caption_box = page.locator("div[contenteditable='true'][role='textbox']").last
                    caption_box.wait_for(state="visible", timeout=12000)
                    caption_box.focus()

                    lines = caption.split("\n")
                    for l_idx, line in enumerate(lines):
                        if line:
                            caption_box.type(line, delay=random.randint(6, 16))
                        if l_idx < len(lines) - 1:
                            page.keyboard.press("Shift+Enter")
                            time.sleep(random.uniform(0.12, 0.3))

                    time.sleep(random.uniform(2.5, 4.5))
                    page.keyboard.press("Enter")
                    time.sleep(random.uniform(3.5, 5.5))
                    print("      [✔] Oferta postada com foto real e legenda!")
                    return True
            except Exception as img_err:
                print(f"      [!] Foto falhou ({img_err}). Enviando com prévia de link...")

        chat_box = page.locator("footer div[contenteditable='true']").first
        chat_box.wait_for(state="visible", timeout=15000)
        chat_box.focus()

        lines = caption.split("\n")
        for l_idx, line in enumerate(lines):
            if line:
                chat_box.type(line, delay=random.randint(6, 14))
            if l_idx < len(lines) - 1:
                page.keyboard.press("Shift+Enter")
                time.sleep(random.uniform(0.1, 0.25))

        tempo_min = 5.0
        tempo_max_extra = 15.0
        inicio_espera = time.time()

        # Em vez de uma espera cega, tenta CONFIRMAR que a prévia com imagem
        # realmente carregou (procura um <img> dentro da área de composição),
        # antes de mandar. Se não confirmar a tempo, manda mesmo assim.
        preview_confirmada = False
        try:
            preview_img = page.locator(
                "footer img, div[data-testid='chat-composer'] img, "
                "div[aria-label*='prévia' i] img, div[aria-label*='preview' i] img"
            ).first
            preview_img.wait_for(state="visible", timeout=int(tempo_max_extra * 1000))
            preview_confirmada = True
        except Exception:
            preview_confirmada = False

        decorrido = time.time() - inicio_espera
        if decorrido < tempo_min:
            time.sleep(tempo_min - decorrido)

        if preview_confirmada:
            print(f"      🖼️ Prévia com imagem confirmada ({decorrido:.1f}s).")
        else:
            print(f"      ⚠️ Não confirmou a imagem da prévia em {tempo_max_extra:.0f}s — enviando mesmo assim.")

        page.keyboard.press("Enter")
        time.sleep(random.uniform(3.0, 5.0))
        print("      [✔] Mensagem de oferta enviada com sucesso!")
        return True

    except Exception as e:
        print(f"      [!] Erro no envio: {e}")
        return False

def enviar_lote_para_whatsapp(
    lote: List[Product],
    historico: Set[str],
    rodada_num: int,
    telefone_pessoal: Optional[str] = None,
    registrar_historico: bool = True,
    aguardar_entre_postagens: bool = True,
) -> int:
    if not lote:
        return 0

    grupo = config.DEFAULT_WHATSAPP_GROUP
    destino = f"o número {telefone_pessoal}" if telefone_pessoal else f"o grupo '{grupo}'"
    print(f"\n📲 Abrindo WhatsApp Web em {destino} para envio de {len(lote)} oferta(s)...")
    sender = WhatsAppSender()
    enviados = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(sender.profile_dir),
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-default-browser-check",
                "--disable-session-crashed-bubble",
                "--disable-features=InfiniteSessionRestore",
                "--no-first-run",
            ],
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        try:
            page.wait_for_selector("div#pane-side, div[role='textbox']", timeout=60000)
        except Exception:
            print("[!] WhatsApp Web demorou a responder. Verifique QR Code ou conexão.")
            context.close()
            return 0

        if telefone_pessoal:
            clean_phone = re.sub(r"\D", "", telefone_pessoal)
            if not clean_phone:
                print("[!] OWNER_WHATSAPP_PHONE não contém um número válido.")
                context.close()
                return 0
            page.goto(
                f"https://web.whatsapp.com/send?phone={clean_phone}",
                wait_until="domcontentloaded",
            )
            try:
                page.locator("footer div[contenteditable='true']").first.wait_for(
                    state="visible", timeout=30000
                )
            except Exception:
                print("[!] Não foi possível abrir sua conversa pessoal no WhatsApp.")
                context.close()
                return 0
        elif not sender.open_group_chat(page, grupo):
            print(f"[!] Não foi possível encontrar ou abrir o grupo '{grupo}'.")
            context.close()
            return 0

        for idx, deal in enumerate(lote, start=1):
            normalizar_produto(deal)
            uid = extrair_id_unico(deal)
            hora = datetime.now().strftime("%H:%M:%S")
            loja = (deal.store or "").upper()
            preco = get_preco_produto(deal)
            desc = deal.discount_percent or 0.0

            print(f"\n[{hora}] 📢 Postando [{idx}/{len(lote)}] [{loja}]")
            print(f"      📌 {deal.title[:60]}...")
            print(f"      💰 R$ {preco:.2f} ({desc:.0f}% OFF)")
            print(f"      🔗 Link: {deal.url}")

            caption = format_single_deal_message(deal, idx, len(lote))
            sucesso = postar_com_comportamento_humano(page, deal, caption)

            if sucesso:
                enviados += 1
                if registrar_historico:
                    historico.add(uid)
                    salvar_historico(historico)

            if idx < len(lote) and aguardar_entre_postagens:
                minutos_espera = random.uniform(config.PAUSA_ENTRE_POSTAGENS_MIN, config.PAUSA_ENTRE_POSTAGENS_MAX)
                segundos = int(minutos_espera * 60)
                proximo = datetime.now() + timedelta(seconds=segundos)
                print(f"\n   🛡️ Pausa anti-ban entre postagens: próxima às {proximo.strftime('%H:%M:%S')} (~{minutos_espera:.1f} min)...")
                while segundos > 0:
                    step = min(60, segundos)
                    time.sleep(step)
                    segundos -= step
                    if segundos > 0 and segundos % 180 == 0:
                        print(f"      ⏳ Restam {segundos // 60} minuto(s) para a próxima postagem...")

        time.sleep(4)
        context.close()
        print(f"\n[✔] Lote #{rodada_num} concluído: {enviados} ofertas entregues!")
        if enviados > 0:
            ESTATISTICAS_DIA["ultima_postagem_sucesso"] = datetime.now()
        return enviados


# ==============================================================================
# DIAGNÓSTICO PERIÓDICO (mensagem individual pra você, não pro grupo)
# ==============================================================================
def montar_mensagem_diagnostico(historico: Set[str]) -> str:
    agora = datetime.now().strftime("%d/%m %H:%M")
    linhas = [
        f"🩺 *Diagnóstico PromoPet Hunter* — {agora}",
        "",
        f"🔄 Rodadas de garimpo hoje: {ESTATISTICAS_DIA['rodadas']}",
        f"📢 Ofertas postadas hoje: {len(historico)}",
    ]

    ultima = ESTATISTICAS_DIA.get("ultima_postagem_sucesso")
    if ultima:
        minutos_atras = int((datetime.now() - ultima).total_seconds() // 60)
        linhas.append(f"✅ Última postagem: {ultima.strftime('%H:%M')} ({minutos_atras} min atrás)")
    else:
        linhas.append("⚠️ Nenhuma postagem confirmada ainda hoje.")

    erros_meli = ESTATISTICAS_DIA.get("erros_meli", 0)
    erros_amz = ESTATISTICAS_DIA.get("erros_amazon", 0)
    if erros_meli or erros_amz:
        linhas.append("")
        linhas.append(f"⚠️ Erros hoje: Mercado Livre {erros_meli}x | Amazon {erros_amz}x")
        linhas.append("_Vale dar uma olhada no terminal se continuar acontecendo._")
    else:
        linhas.append("")
        linhas.append("_Tudo rodando normalmente, sem erros nos scrapers hoje._")

    return "\n".join(linhas)

def enviar_diagnostico(mensagem: str) -> bool:
    """Manda a mensagem de diagnóstico direto pro seu número (conversa individual,
    não pro grupo), usando o link direto do WhatsApp — mais confiável que
    procurar pelo nome na lista."""
    phone = getattr(config, "OWNER_WHATSAPP_PHONE", "")
    if not phone:
        print("   [!] OWNER_WHATSAPP_PHONE não configurado em config.py — pulando diagnóstico.")
        return False

    sender = WhatsAppSender()
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(sender.profile_dir),
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-default-browser-check",
                    "--disable-session-crashed-bubble",
                    "--disable-features=InfiniteSessionRestore",
                    "--no-first-run",
                ],
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            page.set_default_timeout(45000)

            clean_phone = re.sub(r"\D", "", phone)
            encoded_msg = urllib.parse.quote(mensagem)
            page.goto(
                f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_msg}",
                wait_until="domcontentloaded"
            )

            msg_box = page.locator("footer div[contenteditable='true']").first
            msg_box.wait_for(state="visible", timeout=30000)
            time.sleep(1.5)
            page.keyboard.press("Enter")
            time.sleep(3.0)
            print("   [✔] Diagnóstico enviado por WhatsApp!")
            context.close()
            return True
    except Exception as e:
        print(f"   [!] Falha ao enviar diagnóstico: {e}")
        return False

def talvez_enviar_diagnostico(historico: Set[str], forcar: bool = False):
    """Envia o diagnóstico se já tiver passado tempo suficiente desde o último
    (config.DIAGNOSTIC_INTERVAL_MINUTES), ou imediatamente se forcar=True."""
    ultimo = ESTATISTICAS_DIA.get("ultimo_diagnostico_enviado")
    intervalo = timedelta(minutes=getattr(config, "DIAGNOSTIC_INTERVAL_MINUTES", 120))

    if not forcar and ultimo and (datetime.now() - ultimo) < intervalo:
        return

    print("\n📋 Enviando diagnóstico periódico...")
    mensagem = montar_mensagem_diagnostico(historico)
    if enviar_diagnostico(mensagem):
        ESTATISTICAS_DIA["ultimo_diagnostico_enviado"] = datetime.now()


# ==============================================================================
# CONTROLE DE HORÁRIO OPERACIONAL
# ==============================================================================
def esta_no_horario_operacional() -> bool:
    agora = datetime.now()
    return config.START_HOUR <= agora.hour < config.END_HOUR

def aguardar_horario_comercial():
    while not esta_no_horario_operacional():
        agora = datetime.now()
        if agora.hour >= config.END_HOUR:
            proximo_inicio = (agora + timedelta(days=1)).replace(hour=config.START_HOUR, minute=0, second=0, microsecond=0)
        else:
            proximo_inicio = agora.replace(hour=config.START_HOUR, minute=0, second=0, microsecond=0)

        tempo_espera = (proximo_inicio - agora).total_seconds()
        horas = int(tempo_espera // 3600)
        minutos = int((tempo_espera % 3600) // 60)

        print("\n" + "🌙" * 38)
        print(f" [MODO NOTURNO / STANDBY] Horário atual: {agora.strftime('%H:%M:%S')}")
        print(f" [JANELA OPERACIONAL] O bot opera diariamente das {config.START_HOUR:02d}:00 às {config.END_HOUR:02d}:00.")
        print(f" [RETORNO] Próximo disparo programado para: {proximo_inicio.strftime('%d/%m/%Y às %H:%M:%S')}")
        print(f" [TEMPO RESTANTE] Faltam aproximadamente {horas}h {minutos}min de descanso.")
        print("🌙" * 38 + "\n")

        tempo_sono = min(900, max(30, int(tempo_espera)))
        time.sleep(tempo_sono)


# ==============================================================================
# LOOP CONTÍNUO DE PRODUÇÃO
# ==============================================================================
def executar_producao():
    print("\n" + "=" * 75)
    print("    🛡️ PROMOPET HUNTER — MERCADO LIVRE & AMAZON 🛡️")
    print("    Nicho exclusivo: Pet Shop / Banho & Tosa")
    print(f"    Janela operacional: {config.START_HOUR:02d}:00 às {config.END_HOUR:02d}:00 (roda o dia todo)")
    print(f"    Só posta desconto real (>= {config.MIN_DISCOUNT_PERCENT:.0f}%) e nunca repete produto no mesmo dia")
    print("=" * 75)

    historico = carregar_historico()
    data_ultimo_reset = datetime.now().date()
    rodada = 1

    while True:
        aguardar_horario_comercial()

        data_hoje = datetime.now().date()
        if data_hoje > data_ultimo_reset:
            print(f"\n🌅 Novo dia iniciado ({data_hoje.strftime('%d/%m/%Y')})! Resetando histórico diário...")
            historico.clear()
            salvar_historico(historico)
            resetar_estatisticas_dia()
            data_ultimo_reset = data_hoje
            rodada = 1

        hora_atual_str = datetime.now().strftime('%H:%M:%S')
        print(f"\n" + "#" * 70)
        print(f"   🚀 INICIANDO RODADA #{rodada} DE GARIMPO [{hora_atual_str}]")
        print(f"   Itens já postados hoje: {len(historico)}")
        print("#" * 70)
        ESTATISTICAS_DIA["rodadas"] += 1

        ofertas = garimpar_ofertas(historico)
        if not ofertas:
            print("\n💤 Nenhuma nova oferta com desconto real no momento. Aguardando 3 minutos...")
            talvez_enviar_diagnostico(historico)
            time.sleep(3 * 60)
            continue

        lote = montar_lote_equilibrado(ofertas, max_items=config.ITENS_POR_LOTE)
        if not lote:
            print("\n💤 Nenhuma oferta passou no filtro para este lote. Aguardando 3 minutos...")
            talvez_enviar_diagnostico(historico)
            time.sleep(3 * 60)
            continue

        print(f"\n🎯 {len(lote)} ofertas selecionadas para postagem:")
        for idx, item in enumerate(lote, 1):
            normalizar_produto(item)
            preco = get_preco_produto(item)
            print(f"   [{idx}] {item.store.upper():<12} | R$ {preco:>6.2f} ({item.discount_percent:>2.0f}% OFF) | {item.title[:45]}...")

        try:
            paths = Exporter.export_all(lote, base_name="lote_postado")
            print(f"   📊 Registro salvo em: {paths['excel']}")
        except Exception as e:
            print(f"   [!] Não foi possível salvar o registro em planilha: {e}")

        enviar_lote_para_whatsapp(lote, historico, rodada)
        talvez_enviar_diagnostico(historico)

        if not esta_no_horario_operacional():
            print(f"\n🔔 [EXPEDIENTE FINALIZADO] Atingido o limite das {config.END_HOUR:02d}:00.")
            aguardar_horario_comercial()
            continue

        pausa_minutos = random.uniform(config.PAUSA_ENTRE_RODADAS_MIN, config.PAUSA_ENTRE_RODADAS_MAX)
        volta = datetime.now() + timedelta(minutes=pausa_minutos)
        print(f"\n☕ Rodada #{rodada} finalizada! Descanso anti-ban: {pausa_minutos:.0f} minutos.")
        print(f"   Próxima rodada de garimpo às {volta.strftime('%H:%M:%S')}...")
        time.sleep(pausa_minutos * 60)
        rodada += 1


def executar_teste_unico():
    """Envia 1 oferta para o número do proprietário, sem usar o grupo nem o histórico."""
    print("\n[*] MODO TESTE — buscando 1 oferta com desconto real agora mesmo...")
    telefone = getattr(config, "OWNER_WHATSAPP_PHONE", "")
    if not telefone:
        print("[!] Configure OWNER_WHATSAPP_PHONE em config.py antes de testar.")
        return
    historico = carregar_historico()
    ofertas = garimpar_ofertas(historico)
    if not ofertas:
        print("[!] Nenhuma oferta qualificada encontrada agora. Tente de novo em alguns minutos.")
        return
    lote = montar_lote_equilibrado(ofertas, max_items=1)
    enviar_lote_para_whatsapp(
        lote,
        historico,
        rodada_num=1,
        telefone_pessoal=telefone,
        registrar_historico=False,
    )


def executar_preview(quantidade: int = 10, enviar_pessoal: bool = False, max_rodadas: int = 6):
    """
    Garimpa até juntar `quantidade` ofertas qualificadas e MOSTRA O RESULTADO
    (terminal e, se pedido, seu WhatsApp pessoal) — NUNCA posta no grupo.
    Usa uma cópia temporária do histórico, então não consome/marca nada do
    histórico real usado pela produção.
    """
    print(f"\n[*] MODO PRÉVIA — garimpando até {quantidade} ofertas (sem postar no grupo)...")
    historico_temp = carregar_historico().copy()  # cópia: não persiste, não afeta a produção
    encontradas: List[Product] = []

    for rodada in range(1, max_rodadas + 1):
        if len(encontradas) >= quantidade:
            break
        print(f"\n--- Rodada de garimpo {rodada}/{max_rodadas} ---")
        novas = garimpar_ofertas(historico_temp)
        for p in novas:
            if len(encontradas) >= quantidade:
                break
            encontradas.append(p)
            historico_temp.add(extrair_id_unico(p))

    if not encontradas:
        print("\n[!] Nenhuma oferta qualificada encontrada nas tentativas. Tente de novo em alguns minutos.")
        return

    print("\n" + "=" * 72)
    print(f"  🎯 PRÉVIA: {len(encontradas)} OFERTA(S) ENCONTRADA(S)")
    print("=" * 72)
    for idx, item in enumerate(encontradas, 1):
        preco = get_preco_produto(item)
        print(f"\n[{idx}] {item.store.upper()} | R$ {preco:.2f} ({item.discount_percent:.0f}% OFF)")
        print(f"    {item.title}")
        print(f"    🔗 {item.url}")

    try:
        paths = Exporter.export_all(encontradas, base_name="preview_termos")
        print(f"\n📊 Registro também salvo em: {paths['excel']}")
    except Exception as e:
        print(f"\n[!] Não foi possível salvar o registro em planilha: {e}")

    if enviar_pessoal:
        print("\n📲 Enviando resumo para o seu WhatsApp pessoal (não vai pro grupo)...")
        mensagem = format_top10_whatsapp_message(encontradas)
        enviar_diagnostico(mensagem)  # mesma técnica: manda direto pro seu número, não busca grupo


def main():
    parser = argparse.ArgumentParser(description="PromoPet Hunter — Mercado Livre & Amazon")
    parser.add_argument("--login-whatsapp", action="store_true", help="Abre o WhatsApp Web para ler o QR Code uma vez")
    parser.add_argument("--test", action="store_true", help="Garimpa e envia 1 oferta para OWNER_WHATSAPP_PHONE")
    parser.add_argument("--diagnostico", action="store_true", help="Envia um diagnóstico de teste agora mesmo, pro seu número")
    parser.add_argument("--preview", type=int, nargs="?", const=10, default=None,
                         metavar="N", help="Garimpa N ofertas (padrão 10) e só MOSTRA no terminal — não posta em lugar nenhum")
    parser.add_argument("--preview-whatsapp", type=int, nargs="?", const=10, default=None,
                         metavar="N", help="Igual --preview, mas também manda o resumo pro seu WhatsApp pessoal (nunca pro grupo)")
    args = parser.parse_args()

    if args.login_whatsapp:
        WhatsAppSender().setup_session()
        return


    if args.test:
        executar_teste_unico()
        return



    if args.diagnostico:
        historico = carregar_historico()
        talvez_enviar_diagnostico(historico, forcar=True)
        return

    if args.preview is not None:
        executar_preview(quantidade=args.preview, enviar_pessoal=False)
        return

    if args.preview_whatsapp is not None:
        executar_preview(quantidade=args.preview_whatsapp, enviar_pessoal=True)
        return

    try:
        executar_producao()
    except KeyboardInterrupt:
        print("\n\n[🛑] PromoPet Hunter pausado pelo usuário. Histórico preservado!")


if __name__ == "__main__":
    main()
