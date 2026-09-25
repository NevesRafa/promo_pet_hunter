from pathlib import Path

# Diretórios
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MEDIA_CACHE_DIR = BASE_DIR / "media_cache"
MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

WHATSAPP_PROFILE_DIR = BASE_DIR / "whatsapp_profile"

HISTORICO_FILE = BASE_DIR / "historico_enviados.json"

# ==============================================================================
# Lojas usadas pelo pipeline principal.
# ==============================================================================
LOJAS_ATIVAS = ["mercadolivre", "amazon"]

# Consultas organizadas por categoria temática. As lojas continuam sendo
# consultadas pela busca textual, mas a rotação por categoria evita repetir
# sempre o mesmo tipo de produto em cada rodada.
CATEGORIAS_MERCADOLIVRE = {
    "maquinas_e_laminas": [
        "maquina de tosa caes profissional",
        "maquina de tosa sem fio",
        "lamina de tosa profissional",
    ],
    "tesouras_e_acessorios_tosa": [
        "tesoura tosa pet profissional",
        "kit tesouras tosa profissional",
        "adaptador lamina tosa",
    ],
    "banho_e_hidratacao": [
        "shampoo pet caes",
        "condicionador pet caes",
        "mascara hidratacao pet",
    ],
    "secagem_e_estrutura": [
        "soprador pet banho e tosa",
        "secador pet profissional",
        "mesa de tosa banho e tosa",
    ],
    "escovas_e_pentes": [
        "rasqueadeira profissional pet",
        "desembolador de nos pet",
        "pente tosa pet profissional",
    ],
    "higiene_e_acessorios": [
        "corta unha pet profissional",
        "limpa ouvido pet",
        "coleira pet profissional",
    ],
}

CATEGORIAS_AMAZON = {
    "maquinas_e_laminas": [
        "maquina tosa caes profissional",
        "maquina tosa sem fio pet",
        "lamina maquina tosa pet",
    ],
    "tesouras_e_acessorios_tosa": [
        "tesoura tosa curva profissional",
        "tesoura desbaste pet",
        "kit tesoura tosa pet",
    ],
    "banho_e_hidratacao": [
        "shampoo pet caes",
        "condicionador pet caes",
        "perfume pet colonia caes",
    ],
    "secagem_e_estrutura": [
        "secador pet profissional",
        "soprador forca pet",
        "mesa tosa pet dobravel",
    ],
    "escovas_e_pentes": [
        "rasqueadeira profissional pet",
        "desembolador pelos pet",
        "pente pet profissional",
    ],
    "higiene_e_acessorios": [
        "cortador unha pet cachorro",
        "limpador ouvido pet",
        "coleira adestramento pet",
    ],
}

# ==============================================================================
# FILTRO ESTRITO: só entra se for produto pet/banho-e-tosa de verdade
# ==============================================================================
PALAVRAS_PROIBIDAS_NAO_PET = [
    # Automotivo
    "automotivo", "automotiva", "carro", "veicular", "moto", "lava auto", "vonixx",
    "cera", "pneu", "lataria", "motor", "parabrisa", "v-floc", "pretinho", "detailer",
    # Cabelo humano / Salão de beleza
    "cabelo humano", "capilar", "salao de beleza", "salão de beleza", "cabeleireiro", "cabeleireira",
    "progressiva", "botox capilar", "alisamento", "tintura", "mechas", "barba", "barbeiro",
    "escova progressiva", "l'oréal", "wella", "haskell",
    # Bebê / Criança
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
    "rasqueadeira", "desembolo", "desembolador", "desemboçador", "soprador pet",
    "secador pet", "maquina tosa", "máquina tosa", "lamina tosa", "lâmina tosa",
    "canil", "toalha pet", "coleira contencao", "focinheira", "shampoo cães", "shampoo pet",
    "pente tosa", "tesoura tosa", "adaptador lamina", "corta unha pet",
    "laco pet", "laço pet", "bandana pet", "gravata pet", "colonia pet", "perfume pet",
    "hidratacao pet", "hidratação pet", "mascara pet", "manteiga hidratação pet"
]

# ==============================================================================
# Critérios de Filtro — promoção só entra se for desconto DE VERDADE
# ==============================================================================
MIN_RATING = 4.2             # Nota mínima (de 1 a 5 estrelas)
MIN_REVIEWS = 5              # Quantidade mínima de avaliações para garantir credibilidade
MIN_DISCOUNT_PERCENT = 10.0  # Desconto mínimo (%) — abaixo disso, não é considerado promoção
PRECO_MIN = 5.0               # Preço mínimo aceito (evita lixo/erro de extração)
PRECO_MAX = 25000.0           # Preço máximo aceito (evita erro de extração)

# Configurações de Discrição e Anti-Bloqueio
DELAY_MIN = 2.5
DELAY_MAX = 5.5
PAGE_TIMEOUT_MS = 30000
MAX_PAGES_PER_TERM = 1

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
]

# ==============================================================================
# Configurações de Afiliados
# ==============================================================================
AMAZON_TAG = "n3v35-20"
MELI_MATT_TOOL = "85415830"
MELI_MATT_WORD = "n3v35"

# ==============================================================================
# Configurações de WhatsApp
# ==============================================================================
DEFAULT_WHATSAPP_GROUP = "Achadinhos banho & tosa 🐶"

# Número que recebe os diagnósticos periódicos (mensagem individual, não vai pro
# grupo) — formato DDI+DDD+número, só dígitos.
OWNER_WHATSAPP_PHONE = "5519996226053"
DIAGNOSTIC_INTERVAL_MINUTES = 120   # a cada quantos minutos mandar um diagnóstico

# Janela operacional de postagem (o bot roda o dia todo dentro dela)
START_HOUR = 8    # Início às 08:00
END_HOUR = 20      # Término às 20:00

# Pausas anti-ban
PAUSA_ENTRE_POSTAGENS_MIN = 10.0   # minutos, entre 1 oferta e outra do mesmo lote
PAUSA_ENTRE_POSTAGENS_MAX = 15.0
PAUSA_ENTRE_RODADAS_MIN = 22.0     # minutos, entre um lote e o próximo garimpo
PAUSA_ENTRE_RODADAS_MAX = 32.0
ITENS_POR_LOTE = 4                 # quantas ofertas por rodada de garimpo
