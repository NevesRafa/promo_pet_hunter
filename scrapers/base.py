import random
import time
import re
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
import config

@dataclass
class Product:
    title: str
    store: str
    current_price: float
    original_price: Optional[float] = None
    discount_percent: float = 0.0
    rating: float = 0.0
    reviews_count: int = 0
    url: str = ""
    free_shipping: bool = False
    image_url: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def is_deal(self) -> bool:
        """Verifica se o produto tem um desconto registrado."""
        return self.discount_percent > 0 or (
            self.original_price is not None and self.original_price > self.current_price
        )

def human_delay(min_s: float = config.DELAY_MIN, max_s: float = config.DELAY_MAX):
    """Pausa com tempo aleatório para simular comportamento humano e evitar bloqueios."""
    sleep_time = random.uniform(min_s, max_s)
    time.sleep(sleep_time)

def parse_price(text: str) -> Optional[float]:
    """Converte strings de preço no formato brasileiro (ex: 'R$ 1.234,56', '159,90' ou '148 reais com 32 centavos') para float."""
    if not text:
        return None
    text = text.strip()
    
    # Suporte a aria-labels do Mercado Livre (ex: '148 reais com 32 centavos' ou '156 reais')
    match_verbal = re.search(r"(\d+)\s*reais(?:\s*com\s*(\d+)\s*centavos)?", text.lower())
    if match_verbal:
        reais = match_verbal.group(1)
        centavos = match_verbal.group(2) or "00"
        if len(centavos) == 1:
            centavos = f"{centavos}0"
        try:
            return float(f"{reais}.{centavos}")
        except ValueError:
            pass

    # Remove R$, espaços e caracteres não numéricos exceto ponto e vírgula
    cleaned = re.sub(r"[^\d,\.]", "", text)
    if not cleaned:
        return None
    try:
        # Se contiver vírgula como decimal (ex: 1.250,50 ou 150,90)
        if "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        return float(cleaned)
    except ValueError:
        return None

def parse_rating(text: str) -> float:
    """Converte texto de avaliação (ex: '4,8 de 5 estrelas', '4.7', 'Avaliação 4.5') para float."""
    if not text:
        return 0.0
    match = re.search(r"(\d+[\.,]\d+)", text)
    if match:
        val_str = match.group(1).replace(",", ".")
        try:
            return float(val_str)
        except ValueError:
            pass
    return 0.0

def parse_reviews_count(text: str) -> int:
    """Extrai número de avaliações (ex: '(1.234)', '560 avaliações', '15k vendidos')."""
    if not text:
        return 0
    text = text.lower().replace(".", "").replace(" ", "")
    # Casos com k (ex: 1.5k)
    match_k = re.search(r"(\d+(?:[\.,]\d+)?)k", text)
    if match_k:
        try:
            val = float(match_k.group(1).replace(",", "."))
            return int(val * 1000)
        except ValueError:
            pass
    
    match = re.search(r"\d+", text)
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            pass
    return 0

def get_stealth_headers() -> dict:
    """Gera cabeçalhos HTTP atualizados e realistas."""
    return {
        "User-Agent": random.choice(config.USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
