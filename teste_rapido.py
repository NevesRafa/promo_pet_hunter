import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scrapers.mercadolivre import MercadoLivreScraper
from executar_1hora import SafeShopeeScraper, SafeAliExpressScraper, construir_link_meli_seguro

print("=" * 60)
print(" 🧪 TESTE RÁPIDO DE CORREÇÕES DAS LOJAS")
print("=" * 60)

# 1. Teste Mercado Livre (Validação de Link)
print("\n[1/3] Testando Mercado Livre...")
ml = MercadoLivreScraper(headless=True)
items_ml = ml.search("shampoo pet", max_items=2)
if items_ml:
    link_corrigido = construir_link_meli_seguro(items_ml[0].url)
    print(f"   [✔] Link original:  {items_ml[0].url}")
    print(f"   [✔] Link Afiliado:  {link_corrigido}")
    if "MLB-MLB" not in link_corrigido and "matt_tool=" in link_corrigido:
        print("   ✅ Mercado Livre: LINK OK (Sem duplicar MLB- e com tags de afiliado)")
    else:
        print("   ❌ Mercado Livre: Link ainda com erro de formatação")
else:
    print("   ❌ Mercado Livre não retornou itens.")

# 2. Teste AliExpress (Validação de Preço Real)
print("\n[2/3] Testando AliExpress...")
ali = SafeAliExpressScraper(headless=True)
items_ali = ali.search("tesoura tosa", max_items=2)
if items_ali:
    for item in items_ali:
        print(f"   [✔] Produto: {item.title[:40]}...")
        print(f"   [✔] Preço Extraído: R$ {item.price:.2f}")
    print("   ✅ AliExpress: PREÇOS OK (Verifique se batem com o valor do item, não com parcelas)")
else:
    print("   ❌ AliExpress não retornou itens.")

# 3. Teste Shopee (Validação de Captura)
print("\n[3/3] Testando Shopee...")
shp = SafeShopeeScraper(headless=True)
items_shp = shp.search("rasqueadeira pet", max_items=2)
print(f"   [✔] Total de produtos encontrados: {len(items_shp)}")
if items_shp:
    for item in items_shp:
        print(f"   [✔] Produto: {item.title[:40]}...")
        print(f"   [✔] Preço: R$ {item.price:.2f} | Link: {item.url}")
    print("   ✅ Shopee: CAPTURA OK")
else:
    print("   ❌ Shopee: Nenhum produto encontrado (verifique seletores ou bloqueio de rede)")

print("\n" + "=" * 60)