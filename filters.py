from typing import List
import config
from scrapers.base import Product

def deduplicate_products(products: List[Product]) -> List[Product]:
    """Remove produtos duplicados por URL ou título muito similar."""
    seen_urls = set()
    seen_titles = set()
    unique = []

    for p in products:
        # Simplifica título para comparação
        simplified_title = "".join(e for e in p.title.lower() if e.isalnum())[:40]
        
        # Se a URL já foi vista ou o título muito similar já foi visto
        clean_url = p.url.split("?")[0] if p.url else ""
        if clean_url and clean_url in seen_urls:
            continue
        if simplified_title and simplified_title in seen_titles:
            continue

        if clean_url:
            seen_urls.add(clean_url)
        if simplified_title:
            seen_titles.add(simplified_title)
            
        unique.append(p)

    return unique

def apply_filters(
    products: List[Product],
    min_rating: float = config.MIN_RATING,
    min_reviews: int = config.MIN_REVIEWS,
    min_discount: float = config.MIN_DISCOUNT_PERCENT,
    require_discount: bool = True
) -> List[Product]:
    """
    Aplica os filtros de qualidade:
    - Boas avaliações (rating >= min_rating)
    - Confiabilidade mínima de avaliações (reviews_count >= min_reviews)
    - Desconto real (discount_percent >= min_discount)
    """
    filtered = []
    for p in products:
        # 1. Filtro de avaliação
        if p.rating < min_rating:
            continue

        # 2. Quantidade mínima de avaliações (evita notas 5.0 com apenas 1 avaliação falsa)
        if p.reviews_count < min_reviews:
            continue

        # 3. Filtro de desconto/promoção
        if require_discount:
            if p.discount_percent < min_discount:
                continue

        filtered.append(p)

    # Ordena por maior desconto e depois por melhor avaliação
    filtered.sort(key=lambda x: (x.discount_percent, x.rating), reverse=True)
    return filtered
