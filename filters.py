from typing import List
from scrapers.base import Product

def deduplicate_products(products: List[Product]) -> List[Product]:
    """Remove produtos duplicados por URL ou título muito similar."""
    seen_urls = set()
    seen_titles = set()
    unique = []

    for p in products:
        # Simplifica título para comparação
        simplified_title = "".join(e for e in (p.title or "").lower() if e.isalnum())[:40]

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
