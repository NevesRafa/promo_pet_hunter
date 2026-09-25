import re
import urllib.parse
from typing import List
import config
from scrapers.base import Product

def build_amazon_affiliate_url(url: str, tag: str = config.AMAZON_TAG) -> str:
    """Gera link de afiliado da Amazon no formato canônico limpo."""
    if not url:
        return ""
    # Busca código ASIN (10 caracteres alfanuméricos)
    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url, re.IGNORECASE)
    if asin_match:
        asin = asin_match.group(1).upper()
        return f"https://www.amazon.com.br/dp/{asin}?tag={tag}"
    
    # Fallback se não identificar o padrão /dp/
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    query_params["tag"] = [tag]
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", new_query, ""))

def build_mercadolivre_affiliate_url(
    url: str,
    matt_tool: str = config.MELI_MATT_TOOL,
    matt_word: str = config.MELI_MATT_WORD
) -> str:
    """Anexa as tags oficiais de afiliado do Mercado Livre de forma limpa."""
    if not url:
        return ""

    mlb_match = re.search(r'MLB-?(\d{8,14})', url, re.IGNORECASE)
    clean_base = url.split("#")[0]
    
    if mlb_match:
        mlb_num = mlb_match.group(1)
        clean_base = f"https://produto.mercadolivre.com.br/MLB-{mlb_num}"

    parsed = urllib.parse.urlparse(clean_base)
    query_params = urllib.parse.parse_qs(parsed.query)

    query_params["matt_tool"] = [matt_tool]
    query_params["matt_word"] = [matt_word]

    new_query = urllib.parse.urlencode(query_params, doseq=True)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", new_query, ""))

def build_shopee_affiliate_url(url: str, affiliate_id: str = config.SHOPEE_AFFILIATE_ID) -> str:
    """Gera link de afiliado da Shopee (quando aprovado) ou retorna o link limpo."""
    if not url:
        return ""
    if not affiliate_id:
        # Ainda em análise pelo usuário: mantém o link original sem quebrar
        return url
    
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    query_params["af_siteid"] = [affiliate_id]
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", new_query, ""))

def apply_affiliate_links(products: List[Product]) -> List[Product]:
    """
    Processa uma lista de produtos, convertendo todos os links para links com comissão.
    Por padrão (config.USE_OFFICIAL_SHORT_LINKS = True), tenta primeiro pegar o link
    curto OFICIAL (via 'Compartilhar' no Mercado Livre / 'Obter link' na Amazon,
    usando a sessão clonada do Chrome) — que já vem com a imagem de prévia certinha.
    Se não conseguir, cai no link manual com a tag de afiliado como reserva.
    """
    updated = []
    for p in products:
        store = p.store.lower()
        original_url = p.url
        official_link = None

        if getattr(config, "USE_OFFICIAL_SHORT_LINKS", False):
            try:
                from link_generator import LinkGenerator
                if "amazon" in store:
                    official_link = LinkGenerator.get_amazon_official_link(original_url)
                elif "mercado" in store or "livre" in store:
                    official_link = LinkGenerator.get_meli_official_link(original_url)
            except Exception as e:
                print(f"    [Afiliado] Falha ao tentar link oficial, usando link manual: {e}")

        if official_link:
            p.url = official_link
        else:
            if "amazon" in store:
                p.url = build_amazon_affiliate_url(original_url)
            elif "mercado" in store or "livre" in store:
                p.url = build_mercadolivre_affiliate_url(original_url)
            elif "shopee" in store:
                p.url = build_shopee_affiliate_url(original_url)

        updated.append(p)
    return updated
