# Perplexo Bot

Bot multi-plataforma (Telegram + WhatsApp) integrado com Perplexity AI para buscas inteligentes com citações.

## Arquitetura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Telegram   │     │  WhatsApp   │     │   MCP Server    │     │  Perplexity  │
│    Bot      │     │    Bot      │     │  (API Wrapper)  │     │    Scraper   │
│  (Python)   │     │  (Node.js)  │     │    (Python)     │     │   (Python)   │
└──────┬──────┘     └──────┬──────┘     └────────┬────────┘     └──────┬───────┘
       │                   │                      │                     │
       └───────────────────┴──────────────────────┘                     │
                           │                                          │
                    ┌──────┴──────┐                                   │
                    │   SQLite    │                                   │
                    │  (Users)    │                                   │
                    └─────────────┘                                   │
                                                                      │
                    ┌─────────────────────────────────────────────────┘
                    │
            ┌───────┴────────┐
            │  Perplexity.ai │
            │    (Web/API)   │
            └────────────────┘
```

## Funcionalidades

### Telegram Bot
- Menu visual com comandos (`/start`, `/modelos`, `/busca`, `/normal`, `/config`, `/ajuda`)
- Seletor de modelos AI com checkmarks (✅)
- Seletor de Focus modes (Web, Academic, Writing, Video, Social, Math, Wolfram)
- Painel de configurações com toggles ON/OFF (🟢/🔴)
- Suporte a imagens (análise visual)
- Suporte a documentos .txt (resumo)
- Suporte a mensagens de voz (transcrição Whisper)

### WhatsApp Bot
- Comandos via menu textual
- Suporte a texto, imagens e documentos
- Sessão persistente com Baileys

### MCP Server
- Wrapper API para Perplexity scraper
- Suporte a múltiplos modelos (Sonar, Sonar Pro, GPT-5.2, Reasoning Pro, Deep Research)
- Suporte a análise de imagens
- Rate limiting integrado

## Modelos Suportados

| Modelo | Velocidade | Contexto | Uso Ideal |
|--------|-----------|----------|-----------|
| Sonar | 10x faster | 128K | Q&A rápido |
| Sonar Pro | Moderate | 200K | Análises detalhadas |
| GPT-5.2 | Moderate | 128K | Coding, raciocínio |
| Reasoning Pro | Moderate | 128K | Problemas complexos |
| Deep Research | Lower | 128K | Pesquisa máxima |

## Deploy

### Docker (Recomendado)

```bash
docker-compose up -d
```

### Manual

```bash
# Instalar dependências
pip install -r requirements.txt
npm install

# Configurar variáveis
cp .env.example .env
nano .env

# Iniciar serviços
pm2 start ecosystem.config.js
```

## Estrutura do Projeto

```
perplexo/
├── src/
│   ├── telegram_bot.py      # Bot Telegram
│   ├── whatsapp_bot.js      # Bot WhatsApp
│   ├── mcp_server.py        # API MCP Server
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── base.py          # Interface base
│   │   ├── standalone.py    # Scraper standalone
│   │   └── henrique.py      # Wrapper henrique-coder
│   ├── database/
│   │   ├── __init__.py
│   │   └── sqlite.py        # Persistência SQLite
│   └── utils/
│       ├── __init__.py
│       ├── rate_limiter.py
│       └── logger.py
├── config/
│   ├── nginx.conf
│   └── pm2.config.js
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── data/                    # SQLite database
├── logs/                    # Logs
├── .env.example
├── requirements.txt
├── package.json
└── README.md
```

## Variáveis de Ambiente

```env
# Telegram
TELEGRAM_TOKEN=seu_token_bot

# Perplexity
PERPLEXITY_SESSION_TOKEN=seu_session_token
PERPLEXITY_API_KEY=sua_api_key_opcional

# Configurações
WEBHOOK_URL=https://seu-dominio.com/telegram
MCP_API_URL=http://127.0.0.1:5000
ADMIN_USER_ID=seu_telegram_id

# Rate Limiting
RATE_LIMIT_MESSAGES=20
RATE_LIMIT_WINDOW=3600

# Database
DATABASE_PATH=data/perplexo.db
```

## Licença

MIT
