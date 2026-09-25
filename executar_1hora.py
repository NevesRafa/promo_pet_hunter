# -*- coding: utf-8 -*-
"""
PromoPet Hunter PROD - Edição Especial Produção Furtiva
Lojas Oficiais: MERCADO LIVRE & AMAZON
Foco Estrito: Nicho Pet Shop, Banho & Tosa e Cuidados com Pets

Destaques desta Versão de Produção:
1. Links 100% Funcionais:
   - Mercado Livre: Preserva o caminho e slug canônico completo, anexando matt_tool e matt_word (Zero erro 404).
   - Amazon: Link canônico limpo com ASIN e tag oficial.
2. Comportamento Humano Anti-Ban no WhatsApp:
   - Digitação ritmada com velocidade variável simulando operador humano.
   - Envio com foto real de alta qualidade ou prévia de link com tempo de renderização.
   - Intervalos orgânicos entre ofertas (10 a 15 minutos) e descanso entre lotes (22 a 32 min).
   - Simulação de pausas naturais e micro-movimentos.
3. Filtro Pet Rigoroso:
   - Permite apenas produtos genuínos de Pet Shop / Banho & Tosa.
   - Bloqueia automotivo, cabelo humano, cosméticos humanos e artigos para bebês humanos.
   - Reconhece colônias e perfumes pet 'cheirinho de bebê'.
4. Estabilidade Total:
   - Mercado Livre e Amazon rodam sequencialmente com o WhatsApp fechado durante o garimpo.
   - O WhatsApp abre exclusivamente para a postagem do lote e fecha com segurança.
   - Compatibilidade total de preços (price e current_price).
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
# GESTÃO DE HISTÓRICO LOCAL (ANTI-REPETIÇÃO)
# ==============================================================================
HISTORICO_FILE = Path("historico_enviados.json")

def carregar_historico() -> Set[str]:
    if not HISTORICO_FILE.exists():
        return set()
    try:
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def salvar_historico(historico: Set[str]):
    try:
        with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
            json.dump(list(historico), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f" [!] Erro ao salvar histórico: {e}")

# ==============================================================================
# NORMALIZAÇÃO DE PREÇOS E PRODUTOS (BLINDAGEM TOTAL)
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

# ==============================================================================
# CONSTRUTORES DE LINKS DE AFILIADOS OFICIAIS (CORRIGIDO PARA ZERO 404)
# ==============================================================================
def construir_link_meli_seguro(url_original: str) -> str:
    """
    Resolve e normaliza qualquer link do Mercado Livre para evitar erro 404:
    1. Desempacota links de anúncios patrocinados (click1 / mclics / redirect) extraindo a URL real de destino.
    2. Suporta produtos de catálogo (/p/MLB...).
    3. Preserva o slug canônico original do produto.
    4. Corrige qualquer duplicidade acidental de prefixo (ex: MLB-MLB...).
    5. Anexa os parâmetros oficiais de afiliado matt_tool e matt_word.
    """
    if not url_original:
        return url_original
    
    url = url_original.strip()
    tool_id = getattr(config, "MELI_TOOL", "85415830")
    word_id = getattr(config, "MELI_WORD", "n3v35")

    # 1. Se for anúncio patrocinado do ML Ads (click1.mercadolivre.com.br ou rotas /mclics/)
    if any(k in url.lower() for k in ["click1.", "/mclics/", "click?", "custom_url="]):
        try:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            for param in ["custom_url", "url", "go", "redirect", "target", "link"]:
                if param in qs and qs[param]:
                    target = urllib.parse.unquote(qs[param][0])
                    if "mercadolivre.com" in target:
                        return construir_link_meli_seguro(target)
        except Exception:
            pass

    # 2. Produto de Catálogo (/p/MLB...)
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

    # 4. Fallback canônico seguro caso a URL venha encurtada ou truncada
    num_match = re.search(r'MLB-?(\d{8,14})', url, re.IGNORECASE)
    if num_match:
        num_code = num_match.group(1)
        return f"https://produto.mercadolivre.com.br/MLB-{num_code}?matt_tool={tool_id}&matt_word={word_id}"

    # 5. Fallback geral
    return f"{clean}?matt_tool={tool_id}&matt_word={word_id}"

def construir_link_amazon_seguro(url_original: str) -> str:
    """
    Localiza o ASIN do produto da Amazon e constrói link canônico limpo.
    """
    tag = getattr(config, "AMAZON_TAG", "n3v35-20")
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
            p.url = construir_link_meli_seguro(p.url)
        elif "amazon" in store:
            p.url = construir_link_amazon_seguro(p.url)
    return produtos

# ==============================================================================
# FILTRO ESTRITO: 100% PET SHOP / BANHO & TOSA
# ==============================================================================
PALAVRAS_PROIBIDAS_NAO_PET = [
    # Automotivo
    "automotivo", "automotiva", "carro", "veicular", "moto", "lava auto", "vonixx",
    "cera", "pneu", "lataria", "motor", "parabrisa", "v-floc", "pretinho", "detailer",
    # Cabelo humano / Salão de beleza
    "cabelo humano", "capilar", "salao de beleza", "salão de beleza", "cabeleireiro", "cabeleireira",
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
    "laco pet", "laço pet", "bandana pet", "gravata pet", "colonia pet", "perfume pet",
    "hidratacao pet", "hidratação pet", "mascara pet", "manteiga hidratação pet"
]

def validar_produto_pet(produto: Product) -> bool:
    titulo = produto.title.lower()
    for termo_proibido in PALAVRAS_PROIBIDAS_NAO_PET:
        if re.search(r'\b' + re.escape(termo_proibido) + r'\b', titulo):
            return False
    return any(termo_pet in titulo for termo_pet in PALAVRAS_OBRIGATORIAS_PET)

def extrair_id_unico(produto: Product) -> str:
    url = produto.url
    m_mlb = re.search(r'(MLB-?\d{8,14})', url, re.IGNORECASE)
    if m_mlb:
        return f"ml_{m_mlb.group(1).upper().replace('-', '')}"
    m_asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url, re.IGNORECASE)
    if m_asin:
        return f"amz_{m_asin.group(1).upper()}"
    return url.split('?')[0].split('#')[0]

# ==============================================================================
# BANCO DE TERMOS INTELIGENTES DE PET SHOP / BANHO & TOSA
# ==============================================================================
TERMOS_MERCADOLIVRE = [
    "colonia pet fixacao duradoura",
    "shampoo pet caes 5 litros galao",
    "soprador pet banho e tosa kyklon",
    "secador pet profissional banho e tosa",
    "maquina de tosa caes profissional",
    "lamina de tosa 10 profissional",
    "lamina de tosa 40 cirurgica",
    "mesa de tosa dobravel banho tosa",
    "toalha alta absorcao banho e tosa",
    "lacos pet banho e tosa atacado",
    "gravatas pet atacado banho tosa",
    "rasqueadeira profissional desembolador pet",
    "tesoura tosa tubarao curva pet"
]

TERMOS_AMAZON = [
    "shampoo pet caes 5 litros",
    "condicionador pet caes 5 litros",
    "mascara hidratacao pet profissional",
    "rasqueadeira profissional pet cachorro",
    "tesoura tosa curva profissional",
    "maquina tosa caes profissional wahl",
    "alicate cortador unha pet cachorro",
    "desembolador de pelos pet cães",
    "perfume pet colonia caes",
    "toalha banho pet alta absorcao"
]

# ==============================================================================
# GARIMPO LIMPO: MERCADO LIVRE + AMAZON
# ==============================================================================
def garimpar_ofertas_prod(historico: Set[str]) -> List[Product]:
    termo_ml = random.choice(TERMOS_MERCADOLIVRE)
    termo_amz = random.choice(TERMOS_AMAZON)

    print("\n" + "=" * 72)
    print("  🐾 GARIMPO PET SHOP / BANHO & TOSA: MERCADO LIVRE & AMAZON 🐾")
    print(f"  Itens já enviados hoje: {len(historico)}")
    print("=" * 72)

    raw_items: List[Product] = []

    # 1. Mercado Livre
    print(f"\n[1/2] 🛒 Mercado Livre: Pesquisando '{termo_ml}'...")
    try:
        ml = MercadoLivreScraper(headless=False)
        items = ml.search(termo_ml, max_items=15)
        print(f"      [✔] {len(items)} produtos encontrados no Mercado Livre")
        raw_items.extend(items)
    except Exception as e:
        print(f"      [!] Erro no Mercado Livre: {e}")

    # 2. Amazon
    print(f"\n[2/2] 📦 Amazon Prime: Pesquisando '{termo_amz}'...")
    try:
        amz = AmazonScraper(headless=True)
        items = amz.search(termo_amz, max_items=15)
        print(f"      [✔] {len(items)} produtos encontrados na Amazon")
        raw_items.extend(items)
    except Exception as e:
        print(f"      [!] Erro na Amazon: {e}")

    # Normalização e Filtragem Estrita
    validos: List[Product] = []
    for p in deduplicate_products(raw_items):
        normalizar_produto(p)
        if not validar_produto_pet(p):
            continue
        uid = extrair_id_unico(p)
        if uid in historico:
            continue
        price = get_preco_produto(p)
        if 5.0 <= price <= 25000.0:
            validos.append(p)

    validos = aplicar_links_afiliados(validos)
    print(f"\n[✔] {len(validos)} Novas Ofertas Inéditas Qualificadas encontradas!")
    return validos

def montar_lote_equilibrado(candidatos: List[Product], max_items: int = 4) -> List[Product]:
    """Garante um mix equilibrado entre Mercado Livre e Amazon, com melhores descontos."""
    if not candidatos:
        return []

    meli = [p for p in candidatos if "mercado" in (p.store or "").lower()]
    amz = [p for p in candidatos if "amazon" in (p.store or "").lower()]

    meli.sort(key=lambda x: (getattr(x, "discount_percent", 0) or 0, getattr(x, "rating", 0) or 0), reverse=True)
    amz.sort(key=lambda x: (getattr(x, "discount_percent", 0) or 0, getattr(x, "rating", 0) or 0), reverse=True)

    lote: List[Product] = []

    # Alterna entre as lojas
    while len(lote) < max_items and (meli or amz):
        if meli and len(lote) < max_items:
            lote.append(meli.pop(0))
        if amz and len(lote) < max_items:
            lote.append(amz.pop(0))

    return lote

# ==============================================================================
# POSTAGEM HUMANA FURTIVA NO WHATSAPP (ANTI-BAN)
# ==============================================================================
def postar_com_comportamento_humano(page: Page, deal: Product, caption: str) -> bool:
    try:
        # Fecha eventuais modais ou caixas abertas
        dialog = page.locator("div[role='dialog']").first
        if dialog.count() > 0 and dialog.is_visible():
            page.keyboard.press("Escape")
            time.sleep(random.uniform(0.6, 1.2))

        # 1. Tenta baixar e enviar a Foto Real
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

                    # Digitação humana linha a linha
                    lines = caption.split("\n")
                    for l_idx, line in enumerate(lines):
                        if line:
                            caption_box.type(line, delay=random.randint(6, 16))
                        if l_idx < len(lines) - 1:
                            page.keyboard.press("Shift+Enter")
                            time.sleep(random.uniform(0.12, 0.3))

                    # Pausa natural antes de enviar
                    time.sleep(random.uniform(2.5, 4.5))
                    page.keyboard.press("Enter")
                    time.sleep(random.uniform(3.5, 5.5))
                    print("      [✔] Oferta postada com foto real e legenda!")
                    return True
            except Exception as img_err:
                print(f"      [!] Foto falhou ({img_err}). Enviando com prévia de link...")

        # 2. Envio via caixa de texto com prévia de link
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

        # Espera carregar a prévia do link do Mercado Livre / Amazon
        tempo_preview = random.uniform(6.5, 9.0)
        print(f"      ⏳ Aguardando prévia de link ({tempo_preview:.1f}s)... ")
        time.sleep(tempo_preview)

        page.keyboard.press("Enter")
        time.sleep(random.uniform(3.0, 5.0))
        print("      [✔] Mensagem de oferta enviada com sucesso!")
        return True

    except Exception as e:
        print(f"      [!] Erro no envio: {e}")
        return False

# ==============================================================================
# CICLO DE DISPARO NO WHATSAPP COM FECHAMENTO SEGURO
# ==============================================================================
def enviar_lote_para_whatsapp(lote: List[Product], historico: Set[str], rodada_num: int) -> int:
    if not lote:
        return 0

    grupo = getattr(config, "DEFAULT_WHATSAPP_GROUP", "Achadinhos banho & tosa 🐶")
    print(f"\n📲 Abrindo WhatsApp Web no grupo '{grupo}' para envio de {len(lote)} oferta(s)...")
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
            print("[!] WhatsApp Web demorou a responder. Verifique QR Code ou conexão.")
            context.close()
            return 0

        if not sender.open_group_chat(page, grupo):
            print(f"[!] Não foi possível encontrar ou abrir o grupo '{grupo}'.")
            context.close()
            return 0

        for idx, deal in enumerate(lote, start=1):
            normalizar_produto(deal)
            uid = extrair_id_unico(deal)
            hora = datetime.now().strftime("%H:%M:%S")
            loja = deal.store.upper()
            preco = get_preco_produto(deal)
            desc = getattr(deal, "discount_percent", 0.0) or 0.0

            print(f"\n[{hora}] 📢 Postando [{idx}/{len(lote)}] [{loja}]")
            print(f"      📌 {deal.title[:60]}...")
            print(f"      💰 R$ {preco:.2f} ({desc:.0f}% OFF)")
            print(f"      🔗 Link: {deal.url}")

            caption = format_single_deal_message(deal, idx, len(lote))
            sucesso = postar_com_comportamento_humano(page, deal, caption)

            if sucesso:
                enviados += 1
                historico.add(uid)
                salvar_historico(historico)

            # Pausa furtiva humana entre postagens do mesmo lote (10 a 15 minutos)
            if idx < len(lote):
                minutos_espera = random.uniform(10.0, 15.0)
                segundos = int(minutos_espera * 60)
                proximo = datetime.now() + timedelta(seconds=segundos)
                print(f"\n   🛡️ [MODO FURTIVO] Pausa anti-ban entre postagens: Próxima às {proximo.strftime('%H:%M:%S')} (~{minutos_espera:.1f} min)...")

                while segundos > 0:
                    step = min(60, segundos)
                    time.sleep(step)
                    segundos -= step
                    if segundos > 0 and segundos % 180 == 0:
                        print(f"      ⏳ Restam {segundos // 60} minuto(s) para a próxima postagem...")

        time.sleep(4)
        context.close()
        print(f"\n[✔] Lote #{rodada_num} concluído: {enviados} ofertas entregues!")
        return enviados

# ==============================================================================
# CONTROLE DE HORÁRIO OPERACIONAL (09:00 ÀS 21:00)
# ==============================================================================
HORA_INICIO = 9   # 09:00 da manhã
HORA_FIM = 21     # 21:00 da noite

def esta_no_horario_operacional() -> bool:
    """Verifica se o momento atual está dentro da janela de postagem (09h às 21h)."""
    agora = datetime.now()
    return HORA_INICIO <= agora.hour < HORA_FIM

def aguardar_horario_comercial():
    """
    Se estiver fora do horário (antes das 09h ou depois das 21h),
    coloca o bot em modo de espera inteligente e avisa a hora de retorno.
    """
    while not esta_no_horario_operacional():
        agora = datetime.now()
        # Calcula quando será o próximo início às 09:00
        if agora.hour >= HORA_FIM:
            proximo_inicio = (agora + timedelta(days=1)).replace(hour=HORA_INICIO, minute=0, second=0, microsecond=0)
        else:
            proximo_inicio = agora.replace(hour=HORA_INICIO, minute=0, second=0, microsecond=0)

        tempo_espera = (proximo_inicio - agora).total_seconds()
        horas = int(tempo_espera // 3600)
        minutos = int((tempo_espera % 3600) // 60)

        print("\n" + "🌙" * 38)
        print(f" [MODO NOTURNO / STANDBY] Horário atual: {agora.strftime('%H:%M:%S')}")
        print(f" [JANELA OPERACIONAL] O bot opera diariamente das {HORA_INICIO:02d}:00 às {HORA_FIM:02d}:00.")
        print(f" [RETORNO] Próximo disparo programado para: {proximo_inicio.strftime('%d/%m/%Y às %H:%M:%S')}")
        print(f" [TEMPO RESTANTE] Faltam aproximadamente {horas}h {minutos}min de descanso.")
        print("🌙" * 38 + "\n")

        # Espera em blocos de até 15 minutos para manter a aplicação responsiva
        tempo_sono = min(900, max(30, int(tempo_espera)))
        time.sleep(tempo_sono)

# ==============================================================================
# LOOP CONTÍNUO DE PRODUÇÃO (09:00 ÀS 21:00)
# ==============================================================================
def executar_producao_pet_hunter():
    print("\n" + "=" * 75)
    print("    🛡️ PROMOPET HUNTER PROD - MERCADO LIVRE & AMAZON 🛡️")
    print("    Ambiente Estável de Produção | Nicho Exclusivo Pet Shop / Banho & Tosa")
    print(f"    Horário Operacional Automático: Diariamente das {HORA_INICIO:02d}:00 às {HORA_FIM:02d}:00")
    print("    Etiqueta ML: n3v35 | Tag Amazon: n3v35-20 | Proteção Anti-Ban Ativa")
    print("=" * 75)

    historico = carregar_historico()
    data_ultimo_reset = datetime.now().date()
    rodada = 1

    while True:
        # Se estiver fora do horário (ex: noite/madrugada), aguarda até as 09:00
        aguardar_horario_comercial()

        # Reset diário de histórico para permitir novas promoções em novo dia
        data_hoje = datetime.now().date()
        if data_hoje > data_ultimo_reset:
            print(f"\n🌅 Novo dia iniciado ({data_hoje.strftime('%d/%m/%Y')})! Resetando histórico diário...")
            historico.clear()
            salvar_historico(historico)
            data_ultimo_reset = data_hoje
            rodada = 1

        hora_atual_str = datetime.now().strftime('%H:%M:%S')
        print(f"\n" + "#" * 70)
        print(f"   🚀 INICIANDO RODADA #{rodada} DE GARIMPO [{hora_atual_str}]")
        print(f"   Janela de Operação: 09:00 às 21:00 | Itens já postados hoje: {len(historico)}")
        print("#" * 70)

        # 1. Garimpa Mercado Livre e Amazon com WhatsApp FECHADO (Zero Conflito)
        ofertas = garimpar_ofertas_prod(historico)

        if not ofertas:
            print("\n💤 Nenhuma nova oferta qualificada no momento. Aguardando 3 minutos...")
            time.sleep(3 * 60)
            continue

        # 2. Seleciona até 4 super ofertas equilibradas
        lote = montar_lote_equilibrado(ofertas, max_items=4)

        if not lote:
            print("\n💤 Nenhuma oferta passou no filtro para este lote. Aguardando 3 minutos...")
            time.sleep(3 * 60)
            continue

        print(f"\n🎯 {len(lote)} Super Ofertas Selecionadas para Postagem:")
        for idx, item in enumerate(lote, 1):
            normalizar_produto(item)
            preco = get_preco_produto(item)
            desc = getattr(item, "discount_percent", 0.0) or 0.0
            print(f"   [{idx}] {item.store.upper():<12} | R$ {preco:>6.2f} ({desc:>2.0f}% OFF) | {item.title[:45]}...")

        # 3. Posta no WhatsApp de forma furtiva
        enviar_lote_para_whatsapp(lote, historico, rodada)

        # Se após a postagem o horário das 21h for atingido, entra em standby
        if not esta_no_horario_operacional():
            print(f"\n🔔 [EXPEDIENTE FINALIZADO] Atingido o limite das {HORA_FIM:02d}:00.")
            aguardar_horario_comercial()
            continue

        # 4. Pausa de descanso natural entre rodadas (22 a 32 minutos)
        pausa_minutos = random.uniform(22.0, 32.0)
        volta = datetime.now() + timedelta(minutes=pausa_minutos)
        print(f"\n☕ [MODO FURTIVO] Rodada #{rodada} finalizada com sucesso!")
        print(f"   Descanso orgânico anti-ban: {pausa_minutos:.0f} minutos.")
        print(f"   Próxima rodada de garimpo iniciará às {volta.strftime('%H:%M:%S')}...")

        time.sleep(pausa_minutos * 60)
        rodada += 1

if __name__ == "__main__":
    try:
        executar_producao_pet_hunter()
    except KeyboardInterrupt:
        print("\n\n[🛑] PromoPet Hunter pausado pelo usuário. Histórico preservado!")
