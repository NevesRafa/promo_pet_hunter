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
# LOJAS ATIVAS NESTA VERSÃO
# Shopee e AliExpress ficam para a próxima versão — os scrapers continuam no
# projeto (em scrapers/_proxima_versao/), só não são usados por enquanto.
# ==============================================================================
LOJAS_ATIVAS = ["mercadolivre", "amazon"]

# ==============================================================================
# TERMOS DE BUSCA — cobrindo toda a linha de Banho & Tosa / Petshop,
# de máquinas profissionais até laços e acessórios.
#
# TERMOS "AMPLOS" (categoria): buscas largas que trazem uma variedade grande
# de tipos de produto numa tacada só — funcionam quase como navegar a
# categoria inteira, sem precisar de uma URL de categoria separada (o
# Mercado Livre nem tem uma URL de categoria estável fora da busca normal).
# Ficam misturados na mesma lista, e o garimpo sorteia entre eles.
# ==============================================================================
TERMOS_AMPLOS_MERCADOLIVRE = [
    "banho e tosa",
    "banho tosa",
    "equipamento banho tosa",
    "tudo para banho e tosa",
    "kit banho e tosa",
    "material banho tosa",
    "petshop banho e tosa",
]

TERMOS_MERCADOLIVRE = TERMOS_AMPLOS_MERCADOLIVRE + [
    # Máquinas e tosa
    "maquina de tosa caes profissional",
    "maquina de tosa sem fio",
    "lamina de tosa 10 profissional",
    "lamina de tosa 40 cirurgica",
    "adaptador lamina tosa",
    "tesoura tosa tubarao curva pet",
    "tesoura desbastadora pet",
    "kit tesouras tosa profissional",
    # Banho
    "shampoo pet caes 5 litros galao",
    "condicionador pet caes 5 litros",
    "mascara hidratacao pet profissional",
    "colonia pet fixacao duradoura",
    "perfume pet cheirinho de bebe",
    "banheira pet dobravel",
    # Secagem
    "soprador pet banho e tosa",
    "secador pet profissional banho e tosa",
    "secador forca pet gaiola",
    # Estrutura e mesa
    "mesa de tosa dobravel banho tosa",
    "mesa hidraulica pet profissional",
    "tanque banho pet inox",
    "gaiola secagem pet",
    # Escovas e pentes
    "rasqueadeira profissional desembolador pet",
    "escova desembolo pet",
    "pente tosa pet profissional",
    "luva tira pelo pet",
    "desembolador de nos pet",
    # Higiene e cuidados
    "corta unha pet profissional",
    "alicate unha cachorro",
    "limpa ouvido pet",
    "escova dental pet kit",
    "toalha alta absorcao banho e tosa",
    "avental pet shop impermeavel",
    # Acessórios e enfeites
    "lacos pet banho e tosa atacado",
    "gravatas pet atacado banho tosa",
    "bandana pet atacado",
    "coleira contencao banho tosa",
    "focinheira pet ajustavel",
]

TERMOS_AMPLOS_AMAZON = [
    "pet shop banho e tosa",
    "kit banho e tosa pet",
    "equipamento pet shop tosa",
    "acessorios banho e tosa pet",
]

TERMOS_AMAZON = TERMOS_AMPLOS_AMAZON + [
    # Máquinas e tosa
    "maquina tosa caes profissional wahl",
    "maquina tosa sem fio pet",
    "lamina maquina tosa pet",
    "tesoura tosa curva profissional",
    "tesoura desbaste pet",
    # Banho
    "shampoo pet caes 5 litros",
    "condicionador pet caes 5 litros",
    "mascara hidratacao pet profissional",
    "perfume pet colonia caes",
    "banheira dobravel pet",
    # Secagem
    "secador pet profissional",
    "soprador forca pet",
    # Estrutura
    "mesa tosa pet dobravel",
    "tanque pet banho inox",
    # Escovas e pentes
    "rasqueadeira profissional pet cachorro",
    "desembolador de pelos pet caes",
    "escova pet remove pelos",
    "pente pet profissional",
    # Higiene
    "alicate cortador unha pet cachorro",
    "limpador de ouvido pet",
    "toalha banho pet alta absorcao",
    "avental pet shop profissional",
    # Acessórios
    "laco pet atacado",
    "bandana cachorro atacado",
    "coleira adestramento pet",
    "focinheira cachorro ajustavel",
]

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
