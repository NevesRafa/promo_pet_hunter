import os
from pathlib import Path

# Diretórios
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Termos de busca focados em Banho e Tosa e Petshop
DEFAULT_SEARCH_TERMS = [
    "maquina de tosa profissional",
    "soprador pet banho e tosa",
    "secador pet profissional",
    "shampoo pet 5 litros",
    "tesoura tosa profissional",
    "mesa de tosa",
    "rasqueadeira profissional pet",
    "lamina de tosa 10"
]

# Critérios de Filtro
MIN_RATING = 4.2            # Nota mínima (de 1 a 5 estrelas)
MIN_REVIEWS = 5             # Quantidade mínima de avaliações para garantir credibilidade
MIN_DISCOUNT_PERCENT = 10.0 # Desconto mínimo (em %) para considerar promoção real

# Configurações de Discrição e Anti-Bloqueio
DELAY_MIN = 2.5             # Tempo mínimo de espera em segundos entre requisições
DELAY_MAX = 5.5             # Tempo máximo de espera em segundos (jitter humano)
PAGE_TIMEOUT_MS = 30000     # Timeout de carregamento em ms
MAX_PAGES_PER_TERM = 1      # Páginas por termo para manter a varredura rápida e discreta

# User-Agents realistas para alternância
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
]

# Configurações de Afiliados
AMAZON_TAG = "n3v35-20"
MELI_MATT_TOOL = "85415830"
MELI_MATT_WORD = "n3v35"
SHOPEE_AFFILIATE_ID = ""  # Será preenchido assim que aprovado

# Sessões para gerar links curtos OFICIAIS
# Perfis próprios e simples (como o do WhatsApp) — nada de clonar o Chrome
# de verdade. Na primeira vez que precisar, o script pede pra você logar
# manualmente na janela que abre; depois disso fica salvo.
MELI_PROFILE_DIR = BASE_DIR / "meli_profile"
AMAZON_PROFILE_DIR = BASE_DIR / "amazon_profile"
USE_OFFICIAL_SHORT_LINKS = True   # Se True, tenta pegar o link curto oficial antes de usar o link com tag manual

# Configurações de WhatsApp
DEFAULT_WHATSAPP_PHONE = "5519996226053"
DEFAULT_WHATSAPP_GROUP = "Achadinhos banho & tosa 🐶"
WHATSAPP_PROFILE_DIR = BASE_DIR / "whatsapp_profile"
MEDIA_CACHE_DIR = BASE_DIR / "media_cache"
MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Janela de envio para o grupo (09h às 19h)
START_HOUR = 9                   # Início às 09:00
END_HOUR = 20                    # Término às 20:00
MIN_INTERVAL_MINUTES = 35.0      # Intervalo mínimo entre postagens no grupo (minutos)
MAX_INTERVAL_MINUTES = 60.0      # Intervalo máximo entre postagens no grupo (minutos)


