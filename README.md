# 🐾 PromoPet Hunter

Robô de garimpo e postagem automática de promoções **Pet Shop / Banho & Tosa**
no WhatsApp, com afiliado do **Mercado Livre** e da **Amazon**.

> Shopee e AliExpress ficam para a próxima versão. Os scrapers continuam no
> projeto, guardados em `proxima_versao/`, só não são usados por enquanto.

---

## ✅ O que o robô garante

- **Desconto real, sempre.** Só posta produtos com desconto igual ou maior
  que `config.MIN_DISCOUNT_PERCENT` (10% por padrão) — nada de 0% passando
  como promoção.
- **Nunca repete produto no mesmo dia.** Um histórico local
  (`historico_enviados.json`) lembra tudo que já foi postado hoje e reseta
  sozinho à meia-noite.
- **Só produto pet de verdade.** Uma lista de palavras obrigatórias/proibidas
  filtra resultados fora do nicho (automotivo, cabelo humano, bebê, etc.).
- **Roda o dia todo**, dentro da janela configurada (09h–21h por padrão),
  com pausas humanas entre postagens e entre rodadas de garimpo, pra não
  levar bloqueio.
- **Cobertura ampla de produtos**: máquinas de tosa, lâminas, tesouras,
  shampoos, secadores, mesas, rasqueadeiras, laços, bandanas, coleiras e
  mais — veja `config.TERMOS_MERCADOLIVRE` / `config.TERMOS_AMAZON`.

---

## 📋 Instalação

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 🚀 Como usar

### 1. Conectar o WhatsApp (uma vez só)
```bash
python bot.py --login-whatsapp
```
Leia o QR Code com o celular. A sessão fica salva em `whatsapp_profile/`.

### 2. Testar rápido (1 oferta, agora)
```bash
python bot.py --test  # envia uma oferta somente para OWNER_WHATSAPP_PHONE
```
Garimpa e posta uma oferta imediatamente, ignorando a janela de horário —
bom pra confirmar que tudo está funcionando antes de deixar rodando.

### 3. Rodar de verdade (garimpo contínuo)
```bash
python bot.py
```
Fica rodando o dia todo dentro da janela operacional, postando lotes de
`config.ITENS_POR_LOTE` ofertas por rodada, com pausas anti-ban entre
postagens e entre rodadas. Fora do horário, o robô entra em standby e
acorda sozinho no horário configurado.

---

## ⚙️ Ajustes principais (`config.py`)

| O que mexer | Onde |
|---|---|
| Horário de funcionamento | `START_HOUR` / `END_HOUR` |
| Desconto mínimo aceito | `MIN_DISCOUNT_PERCENT` |
| Nota mínima / avaliações mínimas | `MIN_RATING` / `MIN_REVIEWS` |
| Quantas ofertas por rodada | `ITENS_POR_LOTE` |
| Pausas anti-ban | `PAUSA_ENTRE_POSTAGENS_*` / `PAUSA_ENTRE_RODADAS_*` |
| Termos de busca | `TERMOS_MERCADOLIVRE` / `TERMOS_AMAZON` |
| Palavras que barram um produto fora do nicho | `PALAVRAS_PROIBIDAS_NAO_PET` |
| Grupo de WhatsApp de destino | `DEFAULT_WHATSAPP_GROUP` |
| Tags de afiliado | `AMAZON_TAG` / `MELI_MATT_TOOL` / `MELI_MATT_WORD` |

---

## 📁 Estrutura do projeto

- `bot.py` — ponto de entrada único: garimpo, filtros, links de afiliado e postagem.
- `config.py` — todas as configurações num lugar só.
- `filters.py` — deduplicação de produtos coletados.
- `templates.py` — formatação chamativa das mensagens do WhatsApp.
- `whatsapp_sender.py` — automação do WhatsApp Web (login, abrir grupo, postar).
- `media_manager.py` — download da foto real do produto.
- `exporters.py` — registro de cada lote postado em Excel/TXT/CSV (`outputs/`).
- `scrapers/` — coletores do Mercado Livre e da Amazon.
- `proxima_versao/` — Shopee e AliExpress, guardados para a próxima versão.

---

## 📁 Arquivos gerados

- `outputs/lote_postado_*.xlsx` / `.txt` / `.csv` — registro de cada lote postado.
- `historico_enviados.json` — controle de produtos já postados hoje.
- `whatsapp_profile/` e `media_cache/` — dados de sessão e cache, não versionar.
