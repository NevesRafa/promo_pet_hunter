# PromoPet Hunter

Automação local para encontrar e publicar promoções de **Mercado Livre** e
**Amazon** em grupos do WhatsApp. O foco atual é **banho e tosa, pet shop e
cuidados veterinários**, com filtros de qualidade, categorias rotativas,
imagens de produto, links de afiliado e histórico contra repetição.

> O programa usa o WhatsApp Web por automação local. Mantenha o uso moderado,
> respeite as regras das plataformas e teste tudo no seu próprio número antes
> de ativar um grupo.

## Funcionalidades

- Pesquisa rotativa por categorias, não apenas um termo fixo.
- Lojas ativas: Mercado Livre e Amazon.
- Filtro pet com palavras obrigatórias e termos proibidos.
- Desconto mínimo, nota mínima, avaliações mínimas e faixa de preço.
- Deduplicação por produto e histórico diário em `historico_enviados.json`.
- Download e validação da imagem antes do anexo no WhatsApp.
- Links de afiliado configuráveis por perfil.
- Painel local para grupos, categorias e afiliados.
- Teste isolado de uma oferta no número do proprietário.
- Limpeza diária limitada às mensagens próprias que parecem promoções.
- Saudação matinal e mensagem de encerramento no grupo.
- Exportação dos lotes para CSV, TXT e Excel.

## Requisitos

- Windows, macOS ou Linux.
- Python 3.10 ou superior.
- Google Chrome instalado, pois o projeto usa `channel="chrome"`.
- Uma sessão autenticada do WhatsApp Web.
- Conta/logins e links de afiliado válidos nas plataformas usadas.

## Instalação

Na pasta do projeto:

```powershell
pip install -r requirements.txt
playwright install chromium
```

O Playwright é usado pelos scrapers e pelo WhatsApp Web. O Pillow é usado
quando disponível para normalizar imagens incompatíveis.

## Primeiro acesso ao WhatsApp

Execute uma vez:

```powershell
py bot.py --login-whatsapp
```

Leia o QR Code na janela aberta. A sessão fica salva em `whatsapp_profile/`.
Não apague essa pasta enquanto quiser reutilizar o login.

## Painel de configuração

Inicie o painel local:

```powershell
py painel.py
```

Abra o endereço mostrado, normalmente:

```text
http://127.0.0.1:8765
```

O painel permite:

- Selecionar o perfil ativo.
- Criar um novo perfil usando um novo ID, como `cosmeticos_pet`.
- Definir o nome exibido e o grupo do WhatsApp.
- Trocar a tag da Amazon.
- Trocar `matt_tool` e `matt_word` do Mercado Livre.
- Editar as categorias e consultas de cada loja.
- Ativar ou desativar a limpeza diária de promoções.
- Testar uma oferta no número pessoal.
- Iniciar a produção.

As alterações são salvas em `perfis.json`. O `config.py` carrega o perfil
ativo automaticamente quando o bot inicia.

### Formato das categorias

Cada linha representa uma categoria:

```text
shampoos: shampoo pet hidratante, shampoo caes profissional
perfumes: colonia pet, perfume cachorro
higiene: limpa ouvido pet, corta unha pet
```

Use termos que mantenham o contexto pet. O filtro final continua ativo mesmo
quando uma consulta retorna produtos fora do nicho.

## Testes seguros

Antes de publicar em grupo, use:

```powershell
py bot.py --test
```

Esse modo busca uma oferta e envia somente para `OWNER_WHATSAPP_PHONE`. Ele
não abre o grupo e não grava o produto no histórico de produção.

Outros comandos disponíveis:

```powershell
py bot.py --help
py bot.py --preview
py bot.py --preview-whatsapp
py bot.py --diagnostico
```

`--preview` apenas pesquisa e mostra as ofertas. `--preview-whatsapp` envia
um resumo para o número pessoal. `--diagnostico` envia o diagnóstico atual
para o número pessoal.

## Produção

Depois de validar o teste pessoal:

```powershell
py bot.py
```

O bot:

1. Aguarda a janela definida por `START_HOUR` e `END_HOUR`.
2. Escolhe uma categoria para cada loja.
3. Busca produtos no Mercado Livre e na Amazon.
4. Deduplica e aplica os filtros pet, preço, avaliação e desconto.
5. Monta um lote equilibrado entre as lojas.
6. Abre o grupo configurado e publica as ofertas.
7. Registra produtos enviados no histórico.
8. Aguarda a pausa configurada antes da próxima rodada.

Para parar, pressione `Ctrl+C`. O histórico já salvo permanece no disco.

## Limpeza diária do grupo

Quando habilitada, a limpeza ocorre antes do primeiro lote de cada dia, depois
que o bot abre e valida o grupo configurado. Ela tenta apagar somente mensagens
que:

- Foram enviadas pelo próprio número, usando `message-out`.
- Contêm sinais do formato de promoção, como preço, loja e link.
- Estão carregadas na conversa no momento da limpeza.

Configurações:

```python
LIMPAR_PROMOCOES_ANTERIORES = True
LIMITE_LIMPEZA_PROMOCOES = 100
```

A limpeza não é executada no teste pessoal e não remove mensagens de outros
participantes. Como o WhatsApp Web só fornece mensagens carregadas na tela,
ela não garante apagar todo o histórico antigo de uma vez.

## Mensagens de rotina

As mensagens enviadas no grupo podem ser editadas em `config.py`:

```python
MENSAGEM_SAUDACAO = "Bom dia! 🌞🐾 Hoje tem novos achadinhos de banho, tosa e pet shop."
MENSAGEM_ENCERRAMENTO = "Por hoje encerramos os achadinhos. 🐾 Bom descanso e até amanhã!"
```

A saudação é enviada uma vez antes do primeiro lote do dia. O encerramento é
enviado ao final da janela operacional.

## Configurações principais

| Configuração | Função |
|---|---|
| `START_HOUR` / `END_HOUR` | Janela diária de operação |
| `ITENS_POR_LOTE` | Quantidade máxima por rodada |
| `MIN_DISCOUNT_PERCENT` | Desconto mínimo |
| `MIN_RATING` | Nota mínima |
| `MIN_REVIEWS` | Avaliações mínimas |
| `PRECO_MIN` / `PRECO_MAX` | Faixa de preço aceita |
| `PAUSA_ENTRE_POSTAGENS_*` | Pausa entre ofertas |
| `PAUSA_ENTRE_RODADAS_*` | Pausa entre pesquisas |
| `CATEGORIAS_MERCADOLIVRE` | Categorias padrão do Mercado Livre |
| `CATEGORIAS_AMAZON` | Categorias padrão da Amazon |
| `PALAVRAS_OBRIGATORIAS_PET` | Termos que identificam o nicho |
| `PALAVRAS_PROIBIDAS_NAO_PET` | Termos que bloqueiam resultados |
| `DEFAULT_WHATSAPP_GROUP` | Grupo padrão |
| `OWNER_WHATSAPP_PHONE` | Número dos testes e diagnósticos |
| `AMAZON_TAG` | Tag de afiliado Amazon |
| `MELI_MATT_TOOL` / `MELI_MATT_WORD` | Afiliado Mercado Livre |

Para uso por perfis, prefira editar pelo painel em vez de alterar os valores
diretamente no código.

## Estrutura principal

```text
bot.py                 Entrada principal e ciclo de produção
painel.py              Interface local de configuração
perfis.json            Perfis, grupos, categorias e afiliados
config.py              Regras padrão e parâmetros operacionais
scrapers/amazon.py    Scraper Amazon
scrapers/mercadolivre.py Scraper Mercado Livre
scrapers/base.py       Modelo Product e parsers comuns
filters.py             Deduplicação
templates.py            Mensagens do WhatsApp
whatsapp_sender.py     Sessão, grupo e envio de mídia
media_manager.py       Cache e validação de imagens
exporters.py            CSV, TXT e Excel
```

## Arquivos e pastas gerados

- `historico_enviados.json`: IDs dos produtos enviados no dia.
- `outputs/`: lotes exportados em `.csv`, `.txt` e `.xlsx`.
- `media_cache/`: imagens baixadas e validadas.
- `whatsapp_profile/`: sessão persistente do WhatsApp Web.
- `amazon_profile/` e `meli_profile/`: perfis locais usados por ferramentas
  auxiliares ou sessões anteriores.
- `perfis.json`: configuração editável pelo painel.

Perfis de navegador, cache e histórico são dados locais. Não compartilhe essas
pastas nem publique credenciais, cookies ou tokens de afiliado.

## Solução de problemas

### O WhatsApp não abre o grupo

Confirme o nome exato no painel ou em `DEFAULT_WHATSAPP_GROUP`. Execute
novamente `py bot.py --login-whatsapp` se a sessão expirou.

### Nenhuma oferta foi encontrada

Confira o terminal. A busca pode ter retornado produtos sem desconto, sem
avaliação suficiente ou fora do filtro pet. Reduza temporariamente
`MIN_REVIEWS` ou `MIN_DISCOUNT_PERCENT` apenas para diagnóstico.

### A imagem não foi enviada

Verifique `media_cache/`, conexão e o log `[Media]`. O bot envia a mensagem
como texto se o download da imagem falhar.

### O preço mudou depois da publicação

Preços, cupons, estoque e frete das lojas podem mudar após a captura. Por isso
o bot limpa promoções próprias antigas diariamente e as mensagens devem
informar que a oferta está sujeita a alteração.

### O painel não abre

Confira se a porta `8765` está livre. Encerre outra instância com `Ctrl+C` ou
altere `PORT` em `painel.py`.

## Fluxo recomendado

1. Instale dependências.
2. Faça login no WhatsApp.
3. Abra o painel e configure o perfil/grupo.
4. Execute `py bot.py --test`.
5. Confira a mensagem no seu número.
6. Revise categorias e links de afiliado.
7. Inicie `py bot.py` em produção.
8. Observe o primeiro ciclo antes de deixar o processo contínuo.
