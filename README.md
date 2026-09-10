# 🐾 PromoPet Hunter - Rastreador Discreto de Ofertas Petshop & Banho e Tosa

O **PromoPet Hunter** é um script de automação desenvolvido especialmente para o nicho de **Banho e Tosa / Petshop**. Ele varre as plataformas **Mercado Livre**, **Amazon** e **Shopee**, filtrando apenas produtos em **promoção real** e com **ótimas avaliações**, exportando tudo de forma organizada para **Planilha Excel (.xlsx)** e **Bloco de Notas (.txt / .csv)**.

---

## 🛡️ Arquitetura de Discrição e Anti-Bloqueio

Para atender à exigência de discrição máxima e evitar bloqueios de IP ou CAPTCHAs:
1. **Playwright com Stealth Mode:** Oculta propriedades de automação (`navigator.webdriver`, codecs, plugins e assinaturas de headless).
2. **Janela Oculta (Off-Screen):** O navegador roda com coordenadas fora da área visível do monitor (`--window-position=-2400,-2400`), garantindo 100% de passagem por proteções antibot sem janelas pulando na sua tela.
3. **Delays Humanos Aleatórios (Jitter):** Pausas de 2.5 a 5.0 segundos entre requisições para simular a velocidade de leitura humana.
4. **Tratamento de Sessão Persistente:** Reutiliza cookies e tokens locais para manter histórico de navegação válido.

---

## 📋 Pré-requisitos e Instalação

As dependências já estão instaladas no seu ambiente. Caso queira reinstalar ou rodar em outra máquina:

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 🚀 Como Usar

### 1. Conectar seu WhatsApp (Apenas 1 vez)
Para autorizar o envio automático no WhatsApp Web:
```bash
python main.py --login-whatsapp
```
*(Leia o QR Code com o seu celular. A sessão ficará salva permanentemente na pasta `whatsapp_profile/`).*

---

### 2. Testar o Envio de 1 Oferta com FOTO no seu Grupo
Para enviar imediatamente 1 promoção com a **foto real** e a legenda no grupo **"Achadinhos banho & tosa"**:
```bash
python main.py --test-group
```

---

### 3. Iniciar o Agendador Automático (09:00 às 19:00)
Para deixar o robô trabalhando o dia todo com intervalos aleatórios anti-ban:
```bash
python main.py --schedule
```
* **Horário:** Envia apenas entre as **09:00 e 19:00**. Fora desse horário, ele dorme e acorda sozinho às 09:00.
* **Intervalo Anti-Ban:** Aguarda de **35 a 60 minutos** (aleatório) entre cada postagem para não incomodar os membros e não sofrer bloqueio.
* **Foto Real:** Cada oferta sobe com a foto grande nítida do produto e a legenda formatada com seu link de afiliado.

---

### 4. Varredura Normal e Planilhas (Sem WhatsApp)
```bash
python main.py
```

### 3. Selecionar Apenas Determinadas Lojas
```bash
# Apenas Mercado Livre e Amazon:
python main.py --stores mercadolivre amazon

# Apenas Mercado Livre:
python main.py --stores mercadolivre
```

### 4. Personalizar os Filtros de Avaliação e Desconto
```bash
# Produtos com nota mínima de 4.5 e pelo menos 20% de desconto:
python main.py --min-rating 4.5 --min-discount 20.0

# Trazer todos os produtos bem avaliados, mesmo sem desconto registrado:
python main.py --all-deals
```

### 5. Autenticação na Shopee (Opcional)
Se a Shopee exigir verificação de quebra-cabeça/slider:
```bash
python main.py --login-shopee
```
Isso abrirá uma janela do navegador visível para resolver o desafio apenas uma vez. A sessão ficará salva permanentemente na pasta `shopee_profile/` para as próximas buscas automáticas.

---

## 📁 Arquivos Gerados (`outputs/`)

A cada execução, o script gera automaticamente na pasta `outputs/`:
* 📊 **`promocoes_pet_YYYYMMDD_HHMMSS.xlsx`**: Planilha Excel com formatação moderna, cores, percentual de desconto destacado e links clicáveis para abrir direto na loja.
* 📝 **`promocoes_pet_YYYYMMDD_HHMMSS.txt`**: Formatação limpa em texto, perfeita para visualização rápida no **Bloco de Notas**.
* 📁 **`promocoes_pet_YYYYMMDD_HHMMSS.csv`**: Formato universal compatível com qualquer ferramenta de dados (codificação UTF-8 com BOM).

---

## ⚙️ Arquivos do Projeto

* `main.py`: Ponto de entrada do programa e controle de linha de comando.
* `config.py`: Lista de termos padrão, intervalos de tempo e thresholds de nota.
* `filters.py`: Lógica de deduplicação e filtragem de qualidade.
* `exporters.py`: Geradores dos arquivos Excel, Bloco de Notas e CSV.
* `scrapers/`:
  * `mercadolivre.py`: Coletor do Mercado Livre com bypass de PoW/bot challenge.
  * `amazon.py`: Coletor da Amazon com extração de ofertas e avaliações.
  * `shopee.py`: Coletor da Shopee com interceptação de rede e fallback.
