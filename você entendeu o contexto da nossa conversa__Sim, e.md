<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# você entendeu o contexto da nossa conversa

Sim, entendi o **contexto completo**:

## O que rolou até aqui

1. **OpenClaw/contexto**: Você perguntou como o OpenClaw funciona (texto→texto vs. agentic com tools) – respondi que ele **pode** rodar só texto, mas a arquitetura é de agente com execução de ações (shell, arquivos, browser) quando você libera permissões/skills. [1][2]
2. **Vídeo do Breno Vieira**: Você mandou um vídeo sobre "OpenClaw: O Devorador de Tokens" analisando as **7 fraquezas de engenharia de contexto** (append-only sem inteligência, tool results como mensagens normais, compactação reativa tardia ~180k tokens, falta de hierarquia, memory em Markdown, estimativa de tokens imprecisa, compactação usando modelo caro). [1]
**Aprendizado principal**: o custo absurdo vem de acumular histórico+outputs de tools e reenviar tudo a cada chamada, sem descarte inteligente nem cache-control/TTL. [1][2]
3. **Seu projeto "perplexo"**: Você perguntou se eu sabia do `github.com/sonyddr666/perplexo` – eu não consegui acessar o repo. [3]
4. **Perplexity WebUI Scraper**: Você mandou outro repo (`henrique-coder/perplexity-webui-scraper`) que é um **scraper Python** para extrair respostas do Perplexity via web interface (session token) e que pode rodar como **MCP Server**. [1]

## O que eu **presumo** sobre o "perplexo"

Com base no nome e no contexto (você está estudando OpenClaw, viu o scraper de Perplexity MCP, trabalha com agentes/LLMs):

- **Hipótese 1**: "perplexo" é um **clone/alternativa ao Perplexity** (busca + resposta com citações), talvez usando scraping ou API própria de LLM + busca.
- **Hipótese 2**: é um **agente/chatbot com tools** (tipo OpenClaw, mas focado em busca/research), possivelmente integrando com aquele scraper MCP.
- **Hipótese 3**: é um **experimento/framework** pra testar engenharia de contexto/compactação inteligente (os problemas que o vídeo apontou).

**Confirme**: o "perplexo" é um sistema de busca+resposta (tipo Perplexity clone), um agente com tools, ou outra coisa? Aí eu te dou sugestões práticas de arquitetura/próximos passos.

Citações:
[1] README.md https://github.com/henrique-coder/perplexity-webui-scraper/blob/dev/README.md
[2] What is OpenClaw? Your Open-Source AI Assistant for 2026 https://www.digitalocean.com/resources/articles/what-is-openclaw
[3] perplexity-ai · GitHub Topics https://github.com/topics/perplexity-ai

você pode me ajudar a criar algo pra responder via telegram e whatsapp usando o web scrap da perplexity vou rodar na vps

**Perfeito! Vou te ajudar a criar um bot Telegram + WhatsApp que usa o scraper do Perplexity rodando na VPS.** Aqui está a arquitetura completa:

***

## Arquitetura do Sistema

```
[Telegram] ──webhook──> [FastAPI/aiohttp server] ──> [Logic Layer] ──> [Perplexity Scraper MCP]
[WhatsApp] ──Baileys──>                                    │                         │
                                                            └─> [Response Handler] <──┘
```


***

## Stack Técnica

### Backend Principal

- **Python 3.10+** com `python-telegram-bot` (webhooks) [^1_1]
- **Node.js 18+** com `Baileys` para WhatsApp (multi-sessão) [^1_2]
- **Perplexity Scraper** (`henrique-coder/perplexity-webui-scraper`) rodando como MCP Server [^1_3]


### Infraestrutura VPS

- **Reverse Proxy**: Nginx para SSL termination [^1_1]
- **Process Manager**: PM2 para gerenciar Node.js + Python
- **Portas**: 443 (HTTPS) → Nginx → 8000 (Telegram) / 3000 (WhatsApp API)

***

## Implementação Detalhada

### 1. Telegram Bot (Python + Webhooks)

**`telegram_bot.py`**

```python
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
import requests

# Config
TELEGRAM_TOKEN = "SEU_TOKEN_BOT"
WEBHOOK_URL = "https://seu-dominio.com/telegram"
PERPLEXITY_MCP_URL = "http://localhost:5000"  # MCP Server local

async def handle_message(update: Update, context):
    user_query = update.message.text
    
    # Chama Perplexity Scraper via MCP
    response = requests.post(f"{PERPLEXITY_MCP_URL}/search", 
                            json={"query": user_query})
    answer = response.json()["answer"]
    
    await update.message.reply_text(answer)

async def telegram_webhook(request):
    application = request.app["application"]
    await application.update_queue.put(
        Update.de_json(await request.json(), application.bot)
    )
    return web.Response()

async def main():
    app = web.Application()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handler
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Webhook
    app["application"] = application
    app.router.add_post("/telegram", telegram_webhook)
    
    # Set webhook
    await application.bot.set_webhook(url=WEBHOOK_URL)
    
    # Run server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8000)
    await site.start()
    
    await application.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```


***

### 2. WhatsApp Bot (Node.js + Baileys)

**`whatsapp_bot.js`**

```javascript
const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const axios = require('axios');
const pino = require('pino');

const PERPLEXITY_MCP_URL = 'http://localhost:5000';

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('./auth_info_baileys');
    
    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true,
        logger: pino({ level: 'silent' })
    });

    sock.ev.on('creds.update', saveCreds);
    
    sock.ev.on('messages.upsert', async ({ messages }) => {
        const msg = messages[^1_0];
        if (!msg.message || msg.key.fromMe) return;
        
        const userQuery = msg.message.conversation || msg.message.extendedTextMessage?.text;
        
        // Chama Perplexity MCP
        const { data } = await axios.post(`${PERPLEXITY_MCP_URL}/search`, { query: userQuery });
        
        await sock.sendMessage(msg.key.remoteJid, { text: data.answer });
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        if (connection === 'close') {
            const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
            if (shouldReconnect) connectToWhatsApp();
        }
    });
}

connectToWhatsApp();
```


***

### 3. Perplexity MCP Server (Wrapper)

**`perplexity_mcp.py`** (Flask wrapper do scraper)

```python
from flask import Flask, request, jsonify
from perplexity_scraper import PerplexitySession  # Do repo henrique-coder

app = Flask(__name__)

# Inicializa sessão (use seu token)
session = PerplexitySession(session_token="SEU_SESSION_TOKEN")

@app.route('/search', methods=['POST'])
def search():
    query = request.json['query']
    result = session.ask(query)
    return jsonify({"answer": result['text'], "citations": result.get('citations', [])})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
```


***

### 4. Setup da VPS

**Nginx Config** (`/etc/nginx/sites-available/bots`)

```nginx
server {
    listen 443 ssl http2;
    server_name seu-dominio.com;
    
    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;
    
    location /telegram {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
    }
}
```

**PM2 Ecosystem** (`ecosystem.config.js`)

```javascript
module.exports = {
  apps: [
    {
      name: 'telegram-bot',
      script: 'telegram_bot.py',
      interpreter: 'python3'
    },
    {
      name: 'whatsapp-bot',
      script: 'whatsapp_bot.js',
      instances: 1
    },
    {
      name: 'perplexity-mcp',
      script: 'perplexity_mcp.py',
      interpreter: 'python3'
    }
  ]
};
```

**Comandos de Deploy**

```bash
# Instala dependências
npm install @whiskeysockets/baileys axios pino
pip3 install python-telegram-bot aiohttp flask requests

# Inicia todos os serviços
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```


***

## Considerações Importantes

### Obtenção do Session Token (Perplexity)

1. Login no Perplexity.ai via browser [^1_3]
2. DevTools → Application → Cookies → copie `__Secure-next-auth.session-token`
3. Coloque em `perplexity_mcp.py` (renove a cada ~30 dias)

### Rate Limiting

- **Telegram**: 30 msgs/segundo [^1_1]
- **WhatsApp**: Use proxy rotativo (Proxy-Seller) para evitar ban [^1_2]
- **Perplexity**: Limite desconhecido (monitore 429 errors)


### Segurança

- **Telegram**: Valide `bot.token` no webhook handler [^1_4]
- **WhatsApp**: Armazene QR auth em `/auth_info_baileys` fora do repo [^1_5]
- **Firewall**: Bloqueie portas 5000/8000 (só Nginx tem acesso)

***

## Próximos Passos Recomendados

1. **Teste local** com `ngrok` antes do deploy [^1_4]
2. **Adicione fila** (BullMQ + Redis) para limitar concorrência [^1_2]
3. **Logging**: Winston (Node) + Python logging com rotação
4. **Fallback**: Se Perplexity falhar, use Gemini API diretamente (você já tem experiência)

**Precisa de ajuda com alguma parte específica? (setup Nginx, debug Baileys QR, otimizar MCP...)**
<span style="display:none">[^1_10][^1_6][^1_7][^1_8][^1_9]</span>

<div align="center">⁂</div>

[^1_1]: https://github.com/python-telegram-bot/python-telegram-bot/wiki/Webhooks

[^1_2]: https://www.youtube.com/watch?v=Beak6RmBhtw

[^1_3]: https://zapier.com/mcp/perplexity

[^1_4]: https://pinggy.io/blog/how_to_set_up_and_test_telegram_bot_webhook/

[^1_5]: https://www.youtube.com/watch?v=DHEIO9YdRV8

[^1_6]: https://docs.python-telegram-bot.org/en/v21.9/examples.customwebhookbot.html

[^1_7]: https://stackoverflow.com/questions/76884609/deploy-telegram-bot-on-webhooks

[^1_8]: https://www.freecodecamp.org/news/how-to-build-and-deploy-python-telegram-bot-v20-webhooks/

[^1_9]: https://stackoverflow.com/questions/64230870/telegram-bot-with-webhook-on-python

[^1_10]: https://www.youtube.com/watch?v=jePIkhFSwXo


---

# explicações o telegram chama API scrap quero entender

Perfeito! Vou explicar **exatamente como funciona o fluxo** quando o Telegram chama a API do scraper:

***

## Fluxo Completo (Passo a Passo)

### 1. **Usuário manda mensagem no Telegram**

```
Usuário digita: "Qual a temperatura em Paris?"
```


### 2. **Telegram envia webhook POST para sua VPS**

O servidor do Telegram faz uma requisição **HTTP POST** para a URL que você configurou [^2_1]:

```http
POST https://seu-dominio.com/telegram
Content-Type: application/json

{
  "update_id": 123456789,
  "message": {
    "message_id": 456,
    "from": {"id": 987654321, "first_name": "Usuario"},
    "chat": {"id": 987654321, "type": "private"},
    "text": "Qual a temperatura em Paris?"
  }
}
```


### 3. **Nginx encaminha para sua aplicação Python**

```
Nginx (porta 443) → Python/aiohttp (porta 8000)
```


### 4. **Handler do bot processa a mensagem**

Seu código Python **extrai o texto** e **chama a API do scraper**:

```python
async def handle_message(update: Update, context):
    # 1. Extrai texto da mensagem do Telegram
    user_query = update.message.text  # "Qual a temperatura em Paris?"
    chat_id = update.message.chat.id  # 987654321
    
    # 2. Faz requisição HTTP para o scraper Perplexity (MCP Server)
    response = await asyncio.to_thread(
        requests.post,
        "http://localhost:5000/search",  # API local do scraper
        json={"query": user_query},
        timeout=30
    )
    
    # 3. Extrai resposta do JSON
    data = response.json()
    answer = data["answer"]  # "A temperatura em Paris é 15°C..."
    
    # 4. Envia resposta de volta pro usuário
    await context.bot.send_message(
        chat_id=chat_id,
        text=answer
    )
```


### 5. **API do Scraper (MCP Server) processa**

O servidor Flask/FastAPI que você criou:

```python
@app.route('/search', methods=['POST'])
def search():
    # 1. Recebe query
    query = request.json['query']  # "Qual a temperatura em Paris?"
    
    # 2. Chama scraper do Perplexity (faz web scraping)
    session = PerplexitySession(session_token="SEU_TOKEN")
    result = session.ask(query)  # Scraping da resposta
    
    # 3. Retorna JSON
    return jsonify({
        "answer": result['text'],
        "citations": result.get('citations', [])
    })
```


### 6. **Scraper faz requisição ao Perplexity.ai**

O código do `henrique-coder/perplexity-webui-scraper` [^2_2][^2_3]:

```python
# Internamente o scraper faz algo assim:
headers = {
    "Cookie": f"__Secure-next-auth.session-token={session_token}"
}

response = requests.post(
    "https://www.perplexity.ai/api/chat",
    headers=headers,
    json={"query": "Qual a temperatura em Paris?"}
)

# Extrai resposta do HTML/JSON
answer = parse_response(response.text)
```


### 7. **Resposta volta pelo caminho inverso**

```
Perplexity.ai → Scraper → Python handler → Telegram API → Usuário
```


***

## Diagrama do Fluxo Completo

```
┌─────────────┐
│  Usuário    │  "Qual a temperatura em Paris?"
└──────┬──────┘
       │ 1. Envia mensagem
       ▼
┌─────────────────────┐
│  Telegram Servers   │
└──────┬──────────────┘
       │ 2. Webhook POST
       │    https://seu-dominio.com/telegram
       ▼
┌─────────────────────┐
│  Nginx (VPS)        │  :443 → :8000
└──────┬──────────────┘
       │ 3. Proxy reverso
       ▼
┌──────────────────────────────────────┐
│  Python Bot (telegram_bot.py)        │
│                                      │
│  async def handle_message():         │
│    ┌─────────────────────────────┐  │
│    │ 4. POST → localhost:5000    │  │
│    │    /search                  │  │
│    │    {"query": "..."}         │  │
│    └─────────┬───────────────────┘  │
└──────────────┼──────────────────────┘
               │ 5. HTTP request interno
               ▼
┌────────────────────────────────────────┐
│  MCP Server (perplexity_mcp.py)        │
│                                        │
│  @app.route('/search')                 │
│    ┌────────────────────────────────┐ │
│    │ 6. Scraper.ask(query)          │ │
│    │    ↓                           │ │
│    │ POST perplexity.ai/api/chat   │ │
│    │    Headers: session_token     │ │
│    └────────┬───────────────────────┘ │
└─────────────┼──────────────────────────┘
              │ 7. Web scraping
              ▼
┌──────────────────────┐
│  Perplexity.ai       │  "15°C, parcialmente nublado..."
└──────┬───────────────┘
       │ 8. Retorna resposta
       ▼
┌────────────────────────────────────────┐
│  MCP Server                            │
│  return jsonify({"answer": "15°C..."}) │
└──────┬─────────────────────────────────┘
       │ 9. JSON response
       ▼
┌──────────────────────────────────────┐
│  Python Bot                          │
│  await bot.send_message(answer)      │
└──────┬───────────────────────────────┘
       │ 10. Telegram API call
       ▼
┌─────────────────────┐
│  Telegram Servers   │
└──────┬──────────────┘
       │ 11. Entrega mensagem
       ▼
┌─────────────┐
│  Usuário    │  Recebe: "15°C, parcialmente nublado..."
└─────────────┘
```


***

## Código Detalhado com Comentários

### Versão Completa do Handler

```python
import asyncio
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import httpx  # Melhor que requests para async

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "SEU_BOT_TOKEN"
WEBHOOK_URL = "https://seu-dominio.com/telegram"
PERPLEXITY_MCP = "http://127.0.0.1:5000/search"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Fluxo:
    1. Recebe mensagem do Telegram
    2. Faz request HTTP para scraper Perplexity
    3. Envia resposta de volta
    """
    try:
        # PASSO 1: Extrai dados do webhook do Telegram
        user_query = update.message.text
        chat_id = update.message.chat.id
        
        logger.info(f"[RECEBIDO] User {chat_id}: {user_query}")
        
        # PASSO 2: Envia indicador "digitando..."
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # PASSO 3: Chama API do scraper (async)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                PERPLEXITY_MCP,
                json={"query": user_query}
            )
            response.raise_for_status()  # Levanta erro se 4xx/5xx
            data = response.json()
        
        answer = data["answer"]
        citations = data.get("citations", [])
        
        logger.info(f"[SCRAPER] Resposta: {answer[:50]}...")
        
        # PASSO 4: Formata resposta com citações
        if citations:
            answer += "\n\n🔗 Fontes:\n" + "\n".join(
                f"• {c['title']}: {c['url']}" for c in citations[:3]
            )
        
        # PASSO 5: Envia mensagem pro usuário
        await update.message.reply_text(answer)
        
        logger.info(f"[ENVIADO] Para {chat_id}")
        
    except httpx.TimeoutException:
        await update.message.reply_text(
            "⏱️ O scraper demorou muito. Tente novamente."
        )
    except httpx.HTTPError as e:
        logger.error(f"Erro HTTP: {e}")
        await update.message.reply_text("❌ Erro ao buscar resposta.")
    except Exception as e:
        logger.error(f"Erro: {e}")
        await update.message.reply_text("❌ Erro interno.")

async def telegram_webhook(request):
    """Recebe POSTs do Telegram e injeta no bot"""
    application = request.app["application"]
    
    # Converte JSON do Telegram em objeto Update
    update_data = await request.json()
    update = Update.de_json(update_data, application.bot)
    
    # Enfileira update para processamento
    await application.update_queue.put(update)
    
    # IMPORTANTE: Responde 200 OK rapidamente pro Telegram [web:12][web:14]
    return web.Response(status=200)

async def main():
    # Cria servidor web (aiohttp)
    app = web.Application()
    
    # Cria bot do Telegram
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )
    
    # Registra handler de mensagens
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    # Injeta bot no app web
    app["application"] = application
    
    # Rota do webhook
    app.router.add_post("/telegram", telegram_webhook)
    
    # Configura webhook no Telegram
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook configurado: {WEBHOOK_URL}")
    
    # Inicia aplicação
    await application.initialize()
    await application.start()
    
    # Roda servidor web
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8000)
    await site.start()
    
    logger.info("Bot rodando na porta 8000")
    
    # Mantém rodando
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```


***

## Pontos Críticos

### ⚠️ **Webhook DEVE responder 200 OK rapidamente**

O Telegram espera resposta em **até 60 segundos** [^2_4][^2_5]. Se demorar mais:

- Telegram reenvia a mesma mensagem (duplicação)
- `pending_update_count` aumenta

**Solução**: Responda webhook imediatamente e processe async:

```python
async def telegram_webhook(request):
    asyncio.create_task(process_update(update))  # Processa em background
    return web.Response(status=200)  # Responde imediatamente
```


### 🔄 **Alternativa: Responder direto no webhook** [^2_6]

Em vez de chamar `bot.send_message()`, você pode retornar JSON no webhook:

```python
return web.json_response({
    "method": "sendMessage",
    "chat_id": chat_id,
    "text": answer
})
```

**Vantagem**: Reduz 1 chamada de API (útil se bater rate limit 429).

***

## Dependências

```bash
pip install python-telegram-bot aiohttp httpx
```

**Pronto! Agora você entende todo o fluxo de request/response.** Tem alguma parte específica que quer aprofundar? (timeout handling, retry logic, queue system...)
<span style="display:none">[^2_10][^2_7][^2_8][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://pinggy.io/blog/how_to_set_up_and_test_telegram_bot_webhook/

[^2_2]: https://dev.to/oxylabs-io/perplexity-web-scraper-3kkk

[^2_3]: https://oxylabs.io/products/scraper-api/serp/perplexity

[^2_4]: https://stackoverflow.com/questions/40947742/how-to-response-to-telegram-bot-webhook-request-same-request-are-coming-repeate

[^2_5]: https://community.latenode.com/t/how-can-i-send-a-bot-api-request-while-replying-to-a-webhook-in-telegram/5662

[^2_6]: https://github.com/telegram-bot-rb/telegram-bot/issues/59

[^2_7]: https://community.n8n.io/t/telegram-bot-webhook-responses-ai-agent/117183

[^2_8]: https://github.com/eternnoir/pyTelegramBotAPI

[^2_9]: https://app.wizebot.com.br/docs/telegram/bot-manager

[^2_10]: https://stackoverflow.com/questions/78273352/how-to-run-async-function-from-another-thread-in-python-telegram-bot-ptb


---

# a questão é que no app do telegram precisa ser melhor organizado tipo comando /modelos /busca /normal pensa nisso e no API scrap precisar ser compatível com escolha de modelos atuais 2026 e formatos de uso da webscrap

**Perfeito! Vou criar uma arquitetura completa com comandos organizados + API do scraper com suporte aos modelos e modos do Perplexity 2026.**

***

## Arquitetura do Bot Telegram

### Comandos Disponíveis

```
/start        → Menu principal com botões inline
/modelos      → Escolher modelo AI (Sonar, Sonar Pro, GPT-5.2, etc)
/busca        → Modo de busca com Focus (Web, Academic, Video, Social)
/normal       → Conversa normal (sem fontes/citações)
/config       → Ver configurações atuais
/ajuda        → Guia de uso
```


***

## 1. API do Scraper (MCP Server) - Atualizado 2026

### Modelos Disponíveis [^3_1][^3_2][^3_3][^3_4]

```python
# perplexity_mcp.py
from flask import Flask, request, jsonify
from perplexity_scraper import PerplexitySession
from enum import Enum

app = Flask(__name__)

class PerplexityModel(str, Enum):
    """Modelos disponíveis em 2026"""
    SONAR = "sonar"                    # Llama 3.1 70B - Rápido, 128K context [web:22][web:24]
    SONAR_PRO = "sonar-pro"            # 2x retrieval, 200K context [web:24][web:27]
    GPT_52 = "gpt-5.2"                 # OpenAI GPT-5.2 [web:22]
    REASONING_PRO = "reasoning-pro"    # Lógica avançada [web:24]
    DEEP_RESEARCH = "deep-research"    # Pesquisa profunda [web:24]

class FocusMode(str, Enum):
    """Modos de busca [web:26][web:29]"""
    WEB = "web"              # Busca geral
    ACADEMIC = "academic"    # Papers científicos
    WRITING = "writing"      # Escrita criativa
    VIDEO = "video"          # YouTube/Vídeos
    SOCIAL = "social"        # X/Reddit/Social
    MATH = "math"            # Matemática
    WOLFRAM = "wolfram"      # Cálculos avançados

# Inicializa sessão
session = PerplexitySession(session_token="SEU_SESSION_TOKEN")

@app.route('/search', methods=['POST'])
def search():
    """
    Payload:
    {
        "query": "string",
        "model": "sonar|sonar-pro|gpt-5.2|reasoning-pro|deep-research",
        "focus": "web|academic|writing|video|social|math|wolfram",
        "enable_reasoning": bool (opcional),
        "return_citations": bool (default: true)
    }
    """
    data = request.json
    query = data['query']
    model = data.get('model', 'sonar')  # Default: Sonar (mais rápido)
    focus = data.get('focus', 'web')
    enable_reasoning = data.get('enable_reasoning', False)
    return_citations = data.get('return_citations', True)
    
    try:
        # Chama scraper com parâmetros
        result = session.ask(
            query=query,
            model=model,
            focus=focus,
            enable_reasoning=enable_reasoning
        )
        
        response = {
            "answer": result['text'],
            "model_used": model,
            "focus_mode": focus,
            "citations": result.get('citations', []) if return_citations else []
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/models', methods=['GET'])
def list_models():
    """Lista modelos disponíveis"""
    return jsonify({
        "models": [
            {
                "id": "sonar",
                "name": "Sonar",
                "speed": "10x faster",
                "context": "128K tokens",
                "description": "Rápido, ideal para Q&A"
            },
            {
                "id": "sonar-pro", 
                "name": "Sonar Pro",
                "speed": "Moderate",
                "context": "200K tokens",
                "description": "2x retrieval depth, análises detalhadas"
            },
            {
                "id": "gpt-5.2",
                "name": "GPT-5.2",
                "speed": "Moderate",
                "context": "128K tokens",
                "description": "OpenAI, coding e raciocínio avançado"
            },
            {
                "id": "reasoning-pro",
                "name": "Reasoning Pro",
                "speed": "Moderate",
                "context": "128K tokens",
                "description": "Lógica stepwise, problemas complexos"
            },
            {
                "id": "deep-research",
                "name": "Deep Research",
                "speed": "Lower",
                "context": "128K tokens",
                "description": "Pesquisa máxima, relatórios longos"
            }
        ],
        "focus_modes": [
            {"id": "web", "description": "Busca geral na web"},
            {"id": "academic", "description": "Papers científicos"},
            {"id": "writing", "description": "Conteúdo criativo"},
            {"id": "video", "description": "YouTube e vídeos"},
            {"id": "social", "description": "X, Reddit, redes sociais"},
            {"id": "math", "description": "Problemas matemáticos"},
            {"id": "wolfram", "description": "Wolfram Alpha integration"}
        ]
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
```


***

## 2. Bot Telegram com Comandos e Estados

### Estrutura com Conversation Handler [^3_5][^3_6]

```python
# telegram_bot.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
TELEGRAM_TOKEN = "SEU_TOKEN"
WEBHOOK_URL = "https://seu-dominio.com/telegram"
MCP_API = "http://127.0.0.1:5000"

# Estados da conversa
CHOOSING_MODEL, CHOOSING_FOCUS, CHATTING = range(3)

# Storage de preferências por usuário (em produção: use Redis/DB)
user_preferences = {}

def get_user_config(user_id):
    """Retorna config do usuário ou padrão"""
    return user_preferences.get(user_id, {
        'model': 'sonar',
        'focus': 'web',
        'mode': 'normal',  # normal, busca
        'reasoning': False
    })

# ============= COMANDOS =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal /start"""
    keyboard = [
        [InlineKeyboardButton("🤖 Escolher Modelo", callback_data='cmd_modelos')],
        [InlineKeyboardButton("🔍 Modo de Busca", callback_data='cmd_busca')],
        [InlineKeyboardButton("💬 Conversa Normal", callback_data='cmd_normal')],
        [InlineKeyboardButton("⚙️ Configurações", callback_data='cmd_config')],
        [InlineKeyboardButton("❓ Ajuda", callback_data='cmd_ajuda')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌀 **Perplexo Bot** - Powered by Perplexity AI 2026\n\n"
        "Escolha uma opção abaixo ou envie sua pergunta diretamente:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def cmd_modelos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /modelos - Escolher modelo AI"""
    keyboard = [
        [InlineKeyboardButton("⚡ Sonar (Rápido, 10x faster)", callback_data='model_sonar')],
        [InlineKeyboardButton("🔥 Sonar Pro (2x retrieval)", callback_data='model_sonar-pro')],
        [InlineKeyboardButton("🧠 GPT-5.2 (OpenAI)", callback_data='model_gpt-5.2')],
        [InlineKeyboardButton("🤔 Reasoning Pro (Lógica)", callback_data='model_reasoning-pro')],
        [InlineKeyboardButton("📊 Deep Research (Profundo)", callback_data='model_deep-research')],
        [InlineKeyboardButton("« Voltar", callback_data='back_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🤖 **Escolha o Modelo AI**\n\n"
        "• **Sonar**: Mais rápido, ideal para perguntas diretas\n"
        "• **Sonar Pro**: 2x mais fontes, análises detalhadas\n"
        "• **GPT-5.2**: Raciocínio avançado, coding\n"
        "• **Reasoning Pro**: Problemas complexos, lógica stepwise\n"
        "• **Deep Research**: Pesquisa máxima, relatórios longos"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def cmd_busca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /busca - Focus modes"""
    keyboard = [
        [InlineKeyboardButton("🌐 Web (Geral)", callback_data='focus_web')],
        [InlineKeyboardButton("🎓 Academic (Papers)", callback_data='focus_academic')],
        [InlineKeyboardButton("✍️ Writing (Criativo)", callback_data='focus_writing')],
        [InlineKeyboardButton("🎥 Video (YouTube)", callback_data='focus_video')],
        [InlineKeyboardButton("💬 Social (X/Reddit)", callback_data='focus_social')],
        [InlineKeyboardButton("🔢 Math (Matemática)", callback_data='focus_math')],
        [InlineKeyboardButton("🧮 Wolfram (Cálculos)", callback_data='focus_wolfram')],
        [InlineKeyboardButton("« Voltar", callback_data='back_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🔍 **Modo de Busca (Focus)**\n\n"
        "Escolha o tipo de fonte para a pesquisa:\n\n"
        "• **Web**: Busca geral\n"
        "• **Academic**: Papers científicos\n"
        "• **Writing**: Conteúdo criativo\n"
        "• **Video**: YouTube/Vídeos\n"
        "• **Social**: X, Reddit, fóruns\n"
        "• **Math**: Problemas matemáticos\n"
        "• **Wolfram**: Cálculos avançados"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def cmd_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /normal - Conversa sem citações"""
    user_id = update.effective_user.id
    config = get_user_config(user_id)
    config['mode'] = 'normal'
    user_preferences[user_id] = config
    
    text = "💬 **Modo Normal ativado**\n\nAgora vou responder sem citações de fontes."
    
    if update.callback_query:
        await update.callback_query.answer("Modo normal ativado!")
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')

async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /config - Ver configurações"""
    user_id = update.effective_user.id
    config = get_user_config(user_id)
    
    model_names = {
        'sonar': '⚡ Sonar',
        'sonar-pro': '🔥 Sonar Pro',
        'gpt-5.2': '🧠 GPT-5.2',
        'reasoning-pro': '🤔 Reasoning Pro',
        'deep-research': '📊 Deep Research'
    }
    
    focus_names = {
        'web': '🌐 Web', 'academic': '🎓 Academic', 'writing': '✍️ Writing',
        'video': '🎥 Video', 'social': '💬 Social', 'math': '🔢 Math',
        'wolfram': '🧮 Wolfram'
    }
    
    text = (
        f"⚙️ **Suas Configurações**\n\n"
        f"**Modelo**: {model_names[config['model']]}\n"
        f"**Focus**: {focus_names[config['focus']]}\n"
        f"**Modo**: {config['mode'].title()}\n"
        f"**Reasoning**: {'Sim' if config['reasoning'] else 'Não'}"
    )
    
    keyboard = [[InlineKeyboardButton("« Voltar", callback_data='back_main')]]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )

async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ajuda"""
    text = (
        "❓ **Guia de Uso**\n\n"
        "**Comandos:**\n"
        "/start - Menu principal\n"
        "/modelos - Escolher modelo AI\n"
        "/busca - Modo de busca (Focus)\n"
        "/normal - Conversa sem citações\n"
        "/config - Ver configurações\n\n"
        "**Como usar:**\n"
        "1. Escolha o modelo e focus desejados\n"
        "2. Envie sua pergunta diretamente no chat\n"
        "3. O bot responde com citações (exceto no modo normal)\n\n"
        "**Dica**: Use Sonar Pro para pesquisas profundas e Sonar para respostas rápidas."
    )
    
    keyboard = [[InlineKeyboardButton("« Voltar", callback_data='back_main')]]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )

# ============= HANDLERS DE CALLBACK =============

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para botões inline"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Navegação de menus
    if data == 'back_main':
        keyboard = [
            [InlineKeyboardButton("🤖 Escolher Modelo", callback_data='cmd_modelos')],
            [InlineKeyboardButton("🔍 Modo de Busca", callback_data='cmd_busca')],
            [InlineKeyboardButton("💬 Conversa Normal", callback_data='cmd_normal')],
            [InlineKeyboardButton("⚙️ Configurações", callback_data='cmd_config')],
            [InlineKeyboardButton("❓ Ajuda", callback_data='cmd_ajuda')]
        ]
        await query.edit_message_text(
            "🌀 **Perplexo Bot**\n\nEscolha uma opção:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # Seleção de modelo
    elif data.startswith('model_'):
        model = data.replace('model_', '')
        config = get_user_config(user_id)
        config['model'] = model
        config['mode'] = 'busca'  # Ativa modo busca ao escolher modelo
        user_preferences[user_id] = config
        
        await query.answer(f"Modelo {model.upper()} selecionado!")
        await query.edit_message_text(
            f"✅ **Modelo alterado para {model.upper()}**\n\n"
            f"Agora envie sua pergunta no chat.",
            parse_mode='Markdown'
        )
    
    # Seleção de focus
    elif data.startswith('focus_'):
        focus = data.replace('focus_', '')
        config = get_user_config(user_id)
        config['focus'] = focus
        config['mode'] = 'busca'
        user_preferences[user_id] = config
        
        await query.answer(f"Focus {focus.upper()} selecionado!")
        await query.edit_message_text(
            f"✅ **Focus alterado para {focus.upper()}**\n\n"
            f"Agora envie sua pergunta no chat.",
            parse_mode='Markdown'
        )
    
    # Comandos via callback
    elif data == 'cmd_modelos':
        await cmd_modelos(update, context)
    elif data == 'cmd_busca':
        await cmd_busca(update, context)
    elif data == 'cmd_normal':
        await cmd_normal(update, context)
    elif data == 'cmd_config':
        await cmd_config(update, context)
    elif data == 'cmd_ajuda':
        await cmd_ajuda(update, context)

# ============= HANDLER DE MENSAGENS =============

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens do usuário"""
    user_id = update.effective_user.id
    user_query = update.message.text
    config = get_user_config(user_id)
    
    # Envia "digitando..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Chama MCP API
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "query": user_query,
                "model": config['model'],
                "focus": config['focus'],
                "enable_reasoning": config['reasoning'],
                "return_citations": config['mode'] == 'busca'
            }
            
            response = await client.post(f"{MCP_API}/search", json=payload)
            response.raise_for_status()
            data = response.json()
        
        answer = data['answer']
        
        # Formata resposta com metadados
        if config['mode'] == 'busca' and data.get('citations'):
            # Adiciona citações
            answer += "\n\n📚 **Fontes:**\n"
            for i, cite in enumerate(data['citations'][:5], 1):
                answer += f"{i}. [{cite['title']}]({cite['url']})\n"
            
            # Badge do modelo
            answer += f"\n_🤖 Modelo: {data['model_used']} | 🔍 Focus: {data['focus_mode']}_"
        
        await update.message.reply_text(answer, parse_mode='Markdown', disable_web_page_preview=True)
        
    except httpx.TimeoutException:
        await update.message.reply_text("⏱️ Timeout. Tente um modelo mais rápido (/modelos)")
    except Exception as e:
        logger.error(f"Erro: {e}")
        await update.message.reply_text("❌ Erro ao processar. Use /ajuda para mais info.")

# ============= MAIN =============

def main():
    """Inicia o bot"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers de comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("modelos", cmd_modelos))
    app.add_handler(CommandHandler("busca", cmd_busca))
    app.add_handler(CommandHandler("normal", cmd_normal))
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    
    # Handler de botões inline
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Handler de mensagens
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Webhook (para VPS) ou Polling (para teste local)
    if WEBHOOK_URL:
        app.run_webhook(
            listen="127.0.0.1",
            port=8000,
            webhook_url=WEBHOOK_URL,
            url_path="/telegram"
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
```


***

## 3. Estrutura de Pastas

```
/home/usuario/perplexo-bot/
├── telegram_bot.py          # Bot Telegram
├── whatsapp_bot.js          # Bot WhatsApp (Baileys)
├── perplexity_mcp.py        # API wrapper do scraper
├── requirements.txt
├── package.json
├── ecosystem.config.js      # PM2 config
├── .env                     # Variáveis de ambiente
└── auth_info_baileys/       # Sessão WhatsApp
```

**`.env`**

```env
TELEGRAM_TOKEN=seu_token_aqui
PERPLEXITY_SESSION_TOKEN=seu_session_token
WEBHOOK_URL=https://seu-dominio.com/telegram
MCP_API_URL=http://127.0.0.1:5000
```

**`requirements.txt`**

```
python-telegram-bot==21.9
httpx==0.27.0
flask==3.0.0
python-dotenv==1.0.0
# Adicione o scraper: pip install git+https://github.com/henrique-coder/perplexity-webui-scraper
```


***

## 4. Deploy na VPS

```bash
# 1. Clone repos
git clone https://github.com/sonyddr666/perplexo
cd perplexo

# 2. Instala deps
pip3 install -r requirements.txt
npm install

# 3. Configura .env
nano .env

# 4. Testa local (polling)
python3 telegram_bot.py

# 5. Deploy com PM2 (webhook)
pm2 start ecosystem.config.js
pm2 save
```


***

## Diferenças entre os Modelos [^3_4]

| Modelo | Velocidade | Context | Caso de Uso |
| :-- | :-- | :-- | :-- |
| **Sonar** | 10x faster [^3_1] | 128K | Q\&A rápido, respostas diretas |
| **Sonar Pro** | Moderate | 200K | Análises detalhadas, 2x retrieval |
| **GPT-5.2** | Moderate | 128K | Coding, raciocínio criativo |
| **Reasoning Pro** | Moderate | 128K | Problemas complexos, lógica stepwise |
| **Deep Research** | Lower | 128K | Relatórios longos, pesquisa máxima |


***

## Próximos Passos

1. **Persistência**: Trocar `user_preferences` dict por **Redis** ou **SQLite**
2. **Rate Limiting**: Adicionar limite de requests por usuário (ex: 20/hora no Sonar, 5/hora no Deep Research)
3. **WhatsApp**: Replicar mesma lógica de comandos via menu textual
4. **Analytics**: Log de modelos mais usados, queries populares
5. **Cache**: Guardar respostas idênticas por 5min (economiza scraping)

**Precisa de ajuda com alguma parte? (persistência Redis, WhatsApp menu, cache layer...)**
<span style="display:none">[^3_10][^3_7][^3_8][^3_9]</span>

<div align="center">⁂</div>

[^3_1]: https://www.perplexity.ai/hub/blog/meet-new-sonar

[^3_2]: https://www.perplexity.ai/help-center/en/articles/10354919-what-advanced-ai-models-are-included-in-my-subscription

[^3_3]: https://docs.perplexity.ai/getting-started/models

[^3_4]: https://www.datastudios.org/post/perplexity-ai-available-models-all-supported-models-version-differences-capabilities-comparison

[^3_5]: https://stackoverflow.com/questions/51125356/proper-way-to-build-menus-with-python-telegram-bot

[^3_6]: https://docs.python-telegram-bot.org/en/v21.5/telegram.ext.commandhandler.html

[^3_7]: https://www.perplexity.ai/hub/blog/introducing-the-sonar-pro-api

[^3_8]: https://bruteforce.gr/perplexity-ai-how-to-get-better-safer-answers-with-custom-settings

[^3_9]: https://aimlapi.com/models/perplexity-sonar-pro

[^3_10]: https://www.storylane.io/tutorials/how-to-use-perplexity-focus-modes


---

# no telegram possíveis mostragens dentro do /barra vai ter a lista de seleção de modelos nada de / não vai precisar escrever a parte depois do barra ele já vem especificado pra melhor utilização do bot talvez até abrir no /config uma Aba especial tipo um seletor com botões de ativo desativou no telegram visual usar ao máximo essas coisas que telegram disponibiliza dentro da ui do telegram

agora questão de imagens pode ser enviadas ou arquivos de txt pode pensar nisso mais pra frente?

**Perfeito! Vou reformular usando TODOS os recursos nativos do Telegram UI: BotCommand menu, InlineKeyboard, ReplyKeyboard e suporte para imagens/arquivos.**

***

## 1. Menu Visual Nativo do Telegram (BotCommand)

### Configuração no BotFather

```
/setcommands

start - 🏠 Menu Principal
modelos - 🤖 Escolher Modelo AI
busca - 🔍 Modo de Busca (Focus)
normal - 💬 Conversa Normal
config - ⚙️ Configurações
ajuda - ❓ Guia de Uso
```

**Resultado**: Ao digitar `/`, o Telegram mostra a lista visual com descrições, usuário só clica [^4_1][^4_2].

***

## 2. Bot com UI Visual Completa

```python
# telegram_bot.py
import logging
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import httpx
from PIL import Image
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MCP_API = "http://127.0.0.1:5000"

# Storage (em produção: Redis)
user_preferences = {}

def get_user_config(user_id):
    return user_preferences.get(user_id, {
        'model': 'sonar',
        'focus': 'web',
        'mode': 'busca',
        'reasoning': False,
        'return_images': True,
        'return_citations': True
    })

# ============= SETUP DE COMANDOS UI =============

async def post_init(application: Application):
    """Registra comandos no menu do Telegram"""
    commands = [
        BotCommand("start", "🏠 Menu Principal"),
        BotCommand("modelos", "🤖 Escolher Modelo AI"),
        BotCommand("busca", "🔍 Modo de Busca (Focus)"),
        BotCommand("normal", "💬 Conversa Normal"),
        BotCommand("config", "⚙️ Configurações"),
        BotCommand("ajuda", "❓ Guia de Uso")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Comandos registrados no menu do Telegram")

# ============= COMANDO /start =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal com botões inline"""
    user_id = update.effective_user.id
    config = get_user_config(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("🤖 Modelo", callback_data='menu_modelos'),
            InlineKeyboardButton("🔍 Busca", callback_data='menu_busca')
        ],
        [
            InlineKeyboardButton("💬 Normal", callback_data='menu_normal'),
            InlineKeyboardButton("⚙️ Config", callback_data='menu_config')
        ],
        [InlineKeyboardButton("❓ Ajuda", callback_data='menu_ajuda')]
    ]
    
    text = (
        f"🌀 **Perplexo Bot** - Perplexity AI 2026\n\n"
        f"**Configuração Atual:**\n"
        f"🤖 Modelo: `{config['model']}`\n"
        f"🔍 Focus: `{config['focus']}`\n"
        f"💬 Modo: `{config['mode']}`\n\n"
        f"_Envie sua pergunta ou use os botões abaixo:_"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============= COMANDO /modelos - SELETOR VISUAL =============

async def cmd_modelos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista de modelos com seletor visual (checkmark)"""
    user_id = update.effective_user.id
    config = get_user_config(user_id)
    current_model = config['model']
    
    models = [
        ('sonar', '⚡ Sonar', 'Rápido (10x), 128K'),
        ('sonar-pro', '🔥 Sonar Pro', '2x retrieval, 200K'),
        ('gpt-5.2', '🧠 GPT-5.2', 'OpenAI, coding'),
        ('reasoning-pro', '🤔 Reasoning Pro', 'Lógica stepwise'),
        ('deep-research', '📊 Deep Research', 'Pesquisa máxima')
    ]
    
    keyboard = []
    for model_id, emoji_name, description in models:
        # Adiciona ✅ no modelo atual
        prefix = "✅ " if model_id == current_model else ""
        button_text = f"{prefix}{emoji_name}"
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f'set_model_{model_id}'
        )])
    
    keyboard.append([InlineKeyboardButton("« Voltar", callback_data='back_main')])
    
    text = (
        "🤖 **Escolher Modelo AI**\n\n"
        "Selecione o modelo para suas consultas:\n\n"
    )
    for model_id, emoji_name, description in models:
        marker = "✅" if model_id == current_model else "○"
        text += f"{marker} **{emoji_name}**\n   _{description}_\n\n"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ============= COMANDO /busca - SELETOR VISUAL =============

async def cmd_busca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Focus modes com seletor visual"""
    user_id = update.effective_user.id
    config = get_user_config(user_id)
    current_focus = config['focus']
    
    focuses = [
        ('web', '🌐 Web', 'Busca geral'),
        ('academic', '🎓 Academic', 'Papers científicos'),
        ('writing', '✍️ Writing', 'Conteúdo criativo'),
        ('video', '🎥 Video', 'YouTube/Vídeos'),
        ('social', '💬 Social', 'X/Reddit'),
        ('math', '🔢 Math', 'Matemática'),
        ('wolfram', '🧮 Wolfram', 'Cálculos avançados')
    ]
    
    keyboard = []
    for focus_id, emoji_name, description in focuses:
        prefix = "✅ " if focus_id == current_focus else ""
        button_text = f"{prefix}{emoji_name}"
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f'set_focus_{focus_id}'
        )])
    
    keyboard.append([InlineKeyboardButton("« Voltar", callback_data='back_main')])
    
    text = "🔍 **Modo de Busca (Focus)**\n\n"
    for focus_id, emoji_name, description in focuses:
        marker = "✅" if focus_id == current_focus else "○"
        text += f"{marker} **{emoji_name}** - {description}\n"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ============= COMANDO /config - PAINEL DE CONTROLE =============

async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Painel de configurações com toggle switches"""
    user_id = update.effective_user.id
    config = get_user_config(user_id)
    
    # Botões de toggle (ON/OFF visual)
    keyboard = [
        [InlineKeyboardButton(
            f"🧠 Reasoning: {'🟢 ON' if config['reasoning'] else '🔴 OFF'}",
            callback_data='toggle_reasoning'
        )],
        [InlineKeyboardButton(
            f"📚 Citações: {'🟢 ON' if config['return_citations'] else '🔴 OFF'}",
            callback_data='toggle_citations'
        )],
        [InlineKeyboardButton(
            f"🖼️ Imagens: {'🟢 ON' if config['return_images'] else '🔴 OFF'}",
            callback_data='toggle_images'
        )],
        [
            InlineKeyboardButton("🤖 Modelo", callback_data='menu_modelos'),
            InlineKeyboardButton("🔍 Focus", callback_data='menu_busca')
        ],
        [InlineKeyboardButton("« Voltar", callback_data='back_main')]
    ]
    
    text = (
        "⚙️ **Configurações**\n\n"
        f"**Modelo Atual:** `{config['model']}`\n"
        f"**Focus Atual:** `{config['focus']}`\n"
        f"**Modo:** `{config['mode']}`\n\n"
        f"**Opções Avançadas:**\n"
        f"{'🟢' if config['reasoning'] else '🔴'} Reasoning (raciocínio step-by-step)\n"
        f"{'🟢' if config['return_citations'] else '🔴'} Citações de fontes\n"
        f"{'🟢' if config['return_images'] else '🔴'} Retornar imagens\n\n"
        f"_Toque nos botões para alternar ON/OFF_"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ============= COMANDO /normal =============

async def cmd_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa modo conversa normal"""
    user_id = update.effective_user.id
    config = get_user_config(user_id)
    config['mode'] = 'normal'
    config['return_citations'] = False
    user_preferences[user_id] = config
    
    await update.message.reply_text(
        "💬 **Modo Normal ativado**\n\n"
        "Agora respondo sem citações, como uma conversa casual.\n"
        "Use /busca para voltar ao modo pesquisa.",
        parse_mode='Markdown'
    )

# ============= COMANDO /ajuda =============

async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guia de uso"""
    text = (
        "❓ **Guia de Uso do Perplexo Bot**\n\n"
        "**Comandos no menu '/' :**\n"
        "• `/start` - Menu principal\n"
        "• `/modelos` - Escolher modelo AI\n"
        "• `/busca` - Modo de busca (Focus)\n"
        "• `/normal` - Conversa casual\n"
        "• `/config` - Configurações avançadas\n\n"
        "**Recursos:**\n"
        "• Envie texto para perguntas\n"
        "• Envie imagens para análise visual\n"
        "• Envie arquivos .txt para resumir\n\n"
        "**Modelos disponíveis:**\n"
        "⚡ Sonar - Rápido, ideal para Q&A\n"
        "🔥 Sonar Pro - Análises detalhadas\n"
        "🧠 GPT-5.2 - Coding e raciocínio\n"
        "🤔 Reasoning Pro - Lógica complexa\n"
        "📊 Deep Research - Pesquisa máxima\n\n"
        "**Dica:** Use os botões do `/config` para personalizar!"
    )
    
    keyboard = [[InlineKeyboardButton("« Voltar", callback_data='back_main')]]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ============= HANDLERS DE CALLBACK =============

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para todos os botões inline"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Navegação
    if data == 'back_main':
        # Simula /start
        await query.message.delete()
        update.message = query.message
        await start(update, context)
        return
    
    # Menus
    if data == 'menu_modelos':
        await cmd_modelos(update, context)
    elif data == 'menu_busca':
        await cmd_busca(update, context)
    elif data == 'menu_normal':
        await cmd_normal(update, context)
    elif data == 'menu_config':
        await cmd_config(update, context)
    elif data == 'menu_ajuda':
        await cmd_ajuda(update, context)
    
    # Seleção de modelo
    elif data.startswith('set_model_'):
        model = data.replace('set_model_', '')
        config = get_user_config(user_id)
        config['model'] = model
        config['mode'] = 'busca'
        user_preferences[user_id] = config
        
        await query.answer(f"✅ Modelo {model.upper()} selecionado!")
        # Atualiza UI com checkmark
        await cmd_modelos(update, context)
    
    # Seleção de focus
    elif data.startswith('set_focus_'):
        focus = data.replace('set_focus_', '')
        config = get_user_config(user_id)
        config['focus'] = focus
        config['mode'] = 'busca'
        user_preferences[user_id] = config
        
        await query.answer(f"✅ Focus {focus.upper()} selecionado!")
        await cmd_busca(update, context)
    
    # Toggles de config
    elif data == 'toggle_reasoning':
        config = get_user_config(user_id)
        config['reasoning'] = not config['reasoning']
        user_preferences[user_id] = config
        
        status = "ativado" if config['reasoning'] else "desativado"
        await query.answer(f"Reasoning {status}!")
        await cmd_config(update, context)
    
    elif data == 'toggle_citations':
        config = get_user_config(user_id)
        config['return_citations'] = not config['return_citations']
        user_preferences[user_id] = config
        
        status = "ativadas" if config['return_citations'] else "desativadas"
        await query.answer(f"Citações {status}!")
        await cmd_config(update, context)
    
    elif data == 'toggle_images':
        config = get_user_config(user_id)
        config['return_images'] = not config['return_images']
        user_preferences[user_id] = config
        
        status = "ativadas" if config['return_images'] else "desativadas"
        await query.answer(f"Imagens {status}!")
        await cmd_config(update, context)

# ============= HANDLER DE MENSAGENS DE TEXTO =============

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens de texto"""
    user_id = update.effective_user.id
    user_query = update.message.text
    config = get_user_config(user_id)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "query": user_query,
                "model": config['model'],
                "focus": config['focus'],
                "enable_reasoning": config['reasoning'],
                "return_citations": config['return_citations'],
                "return_images": config['return_images']
            }
            
            response = await client.post(f"{MCP_API}/search", json=payload)
            response.raise_for_status()
            data = response.json()
        
        answer = data['answer']
        
        # Adiciona citações se ativado
        if config['return_citations'] and data.get('citations'):
            answer += "\n\n📚 **Fontes:**\n"
            for i, cite in enumerate(data['citations'][:5], 1):
                answer += f"{i}. [{cite.get('title', 'Link')}]({cite['url']})\n"
        
        # Badge de metadados
        answer += f"\n_🤖 {data['model_used']} | 🔍 {data['focus_mode']}_"
        
        await update.message.reply_text(
            answer,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        # Envia imagens se retornadas
        if config['return_images'] and data.get('images'):
            for img_url in data['images'][:3]:  # Máx 3 imagens
                try:
                    await update.message.reply_photo(photo=img_url)
                except Exception as e:
                    logger.warning(f"Erro ao enviar imagem: {e}")
        
    except Exception as e:
        logger.error(f"Erro: {e}")
        await update.message.reply_text(
            "❌ Erro ao processar. Use /config para verificar suas configurações.",
            parse_mode='Markdown'
        )

# ============= HANDLER DE IMAGENS =============

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa imagens enviadas pelo usuário"""
    user_id = update.effective_user.id
    config = get_user_config(user_id)
    
    # Caption da imagem = query do usuário
    caption = update.message.caption or "O que você vê nesta imagem?"
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Download da imagem
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Converte para base64 ou salva temporariamente
        import base64
        photo_b64 = base64.b64encode(photo_bytes).decode()
        
        # Chama MCP API com imagem
        async with httpx.AsyncClient(timeout=90.0) as client:
            payload = {
                "query": caption,
                "model": config['model'],
                "image_base64": photo_b64,
                "focus": "web"
            }
            
            response = await client.post(f"{MCP_API}/vision", json=payload)
            response.raise_for_status()
            data = response.json()
        
        answer = data['answer']
        await update.message.reply_text(answer, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        await update.message.reply_text(
            "❌ Erro ao analisar imagem. Tente novamente ou use outro modelo.",
            parse_mode='Markdown'
        )

# ============= HANDLER DE DOCUMENTOS (.txt, .pdf) =============

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa arquivos de texto"""
    user_id = update.effective_user.id
    config = get_user_config(user_id)
    
    document = update.message.document
    file_name = document.file_name
    
    # Só aceita .txt por enquanto
    if not file_name.endswith('.txt'):
        await update.message.reply_text(
            "⚠️ Por enquanto só aceito arquivos .txt\n"
            "Envie um arquivo de texto para resumir.",
            parse_mode='Markdown'
        )
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Download do arquivo
        file = await document.get_file()
        file_bytes = await file.download_as_bytearray()
        text_content = file_bytes.decode('utf-8')
        
        # Limita tamanho (10KB máx)
        if len(text_content) > 10000:
            text_content = text_content[:10000] + "\n[...truncado]"
        
        # Chama MCP API
        query = f"Resuma o seguinte texto:\n\n{text_content}"
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            payload = {
                "query": query,
                "model": config['model'],
                "focus": "writing",
                "return_citations": False
            }
            
            response = await client.post(f"{MCP_API}/search", json=payload)
            response.raise_for_status()
            data = response.json()
        
        answer = f"📄 **Resumo de {file_name}:**\n\n{data['answer']}"
        await update.message.reply_text(answer, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Erro ao processar documento: {e}")
        await update.message.reply_text(
            "❌ Erro ao processar arquivo. Verifique se é UTF-8.",
            parse_mode='Markdown'
        )

# ============= MAIN =============

def main():
    """Inicia o bot"""
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("modelos", cmd_modelos))
    app.add_handler(CommandHandler("busca", cmd_busca))
    app.add_handler(CommandHandler("normal", cmd_normal))
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Mensagens
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.TEXT, handle_document))
    
    # Webhook ou Polling
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if WEBHOOK_URL:
        app.run_webhook(
            listen="127.0.0.1",
            port=8000,
            webhook_url=WEBHOOK_URL,
            url_path="/telegram"
        )
    else:
        logger.info("🚀 Rodando em modo polling (desenvolvimento)")
        app.run_polling()

if __name__ == "__main__":
    main()
```


***

## 3. API MCP Atualizada (com suporte a imagens/documentos)

```python
# perplexity_mcp.py
from flask import Flask, request, jsonify
from perplexity_scraper import PerplexitySession
import base64
import tempfile
import os

app = Flask(__name__)
session = PerplexitySession(session_token=os.getenv("PERPLEXITY_SESSION_TOKEN"))

@app.route('/search', methods=['POST'])
def search():
    """Endpoint de busca normal"""
    data = request.json
    query = data['query']
    model = data.get('model', 'sonar')
    focus = data.get('focus', 'web')
    enable_reasoning = data.get('enable_reasoning', False)
    return_citations = data.get('return_citations', True)
    return_images = data.get('return_images', False)
    
    try:
        result = session.ask(
            query=query,
            model=model,
            focus=focus,
            enable_reasoning=enable_reasoning
        )
        
        response = {
            "answer": result['text'],
            "model_used": model,
            "focus_mode": focus,
            "citations": result.get('citations', []) if return_citations else [],
            "images": result.get('images', []) if return_images else []
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/vision', methods=['POST'])
def vision():
    """Endpoint para análise de imagens"""
    data = request.json
    query = data['query']
    image_b64 = data['image_base64']
    model = data.get('model', 'sonar-pro')  # Pro para vision
    
    try:
        # Salva imagem temporariamente
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(base64.b64decode(image_b64))
            tmp_path = tmp.name
        
        # Chama scraper com imagem (implementação depende do scraper)
        result = session.ask_with_image(
            query=query,
            image_path=tmp_path,
            model=model
        )
        
        os.unlink(tmp_path)  # Remove temp file
        
        return jsonify({"answer": result['text']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
```


***

## 4. Demonstração da UI no Telegram

### Ao digitar `/` no chat:

```
🏠 /start - Menu Principal
🤖 /modelos - Escolher Modelo AI
🔍 /busca - Modo de Busca (Focus)
💬 /normal - Conversa Normal
⚙️ /config - Configurações
❓ /ajuda - Guia de Uso
```


### Menu /config (com toggles):

```
⚙️ Configurações

Modelo Atual: sonar-pro
Focus Atual: academic
Modo: busca

Opções Avançadas:
🟢 Reasoning (raciocínio step-by-step)
🔴 Citações de fontes
🟢 Retornar imagens

┌─────────────────────────────┐
│ 🧠 Reasoning: 🟢 ON         │ ← Botão clicável
├─────────────────────────────┤
│ 📚 Citações: 🔴 OFF          │
├─────────────────────────────┤
│ 🖼️ Imagens: 🟢 ON           │
├─────────────────────────────┤
│ 🤖 Modelo  │  🔍 Focus       │
├─────────────────────────────┤
│         « Voltar            │
└─────────────────────────────┘
```


### Menu /modelos (com checkmark):

```
🤖 Escolher Modelo AI

✅ ⚡ Sonar
   Rápido (10x), 128K

○ 🔥 Sonar Pro
   2x retrieval, 200K

○ 🧠 GPT-5.2
   OpenAI, coding

[Botões inline para cada modelo]
```


***

## 5. Fluxo de Uso de Imagens/Arquivos

### Exemplo 1: Análise de Imagem

```
Usuário: [Envia foto de gráfico]
         "Explique esse gráfico"

Bot: [typing...]
     "Este gráfico mostra a evolução de vendas Q1-Q4 2025.
     Observa-se crescimento de 23% no Q3, seguido de queda
     de 8% no Q4, possivelmente devido à sazonalidade..."
     
     🤖 sonar-pro | 🔍 web
```


### Exemplo 2: Resumo de Arquivo

```
Usuário: [Envia relatorio.txt]

Bot: [typing...]
     📄 Resumo de relatorio.txt:
     
     O documento apresenta análise financeira do ano fiscal
     2025, destacando receita de $12M (+15% YoY) e EBITDA
     de $3.2M (margem 26.6%). Principais insights:
     - Crescimento orgânico de 12%
     - Redução de custos operacionais em 8%
     - Expansão para 3 novos mercados
     
     🤖 sonar-pro | 🔍 writing
```


***

## Próximos Passos

1. **Persistência**: Migrar `user_preferences` para **Redis** com TTL
2. **Rate Limiting**: Usar `python-telegram-bot-ratelimiter` (5 msgs/min)
3. **Analytics**: Log de comandos mais usados (modelo/focus preferido)
4. **Vision avançado**: Adicionar OCR com Tesseract para texto em imagens
5. **Arquivos PDF**: Usar PyPDF2 para extrair texto
6. **Audio/Voice**: Transcrever notas de voz com Whisper API

**Precisa de ajuda com alguma parte específica? (Redis setup, PDF handler, rate limiter...)**

<div align="center">⁂</div>

[^4_1]: https://stackoverflow.com/questions/51125356/proper-way-to-build-menus-with-python-telegram-bot

[^4_2]: https://docs.python-telegram-bot.org/en/v21.5/telegram.ext.commandhandler.html

