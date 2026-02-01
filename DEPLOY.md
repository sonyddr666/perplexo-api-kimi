# Perplexo Bot - Guia de Deploy

## Índice
1. [Requisitos](#requisitos)
2. [Configuração Inicial](#configuração-inicial)
3. [Deploy com Docker (Recomendado)](#deploy-com-docker)
4. [Deploy Manual](#deploy-manual)
5. [Configuração do Telegram](#configuração-do-telegram)
6. [Configuração do WhatsApp](#configuração-do-whatsapp)
7. [Obtenção do Session Token Perplexity](#obtenção-do-session-token-perplexity)
8. [Configuração de SSL](#configuração-de-ssl)
9. [Troubleshooting](#troubleshooting)

---

## Requisitos

### VPS Recomendada
- **CPU**: 1-2 vCPUs
- **RAM**: 2GB mínimo (4GB recomendado)
- **Disco**: 20GB SSD
- **OS**: Ubuntu 22.04 LTS ou Debian 12
- **Rede**: Portas 80, 443, 5000, 8000

### Software
- Docker 24.0+ e Docker Compose 2.20+
- OU Python 3.11+ e Node.js 18+
- Git
- Nginx (para produção)

---

## Configuração Inicial

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/perplexo.git
cd perplexo
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

Edite o arquivo `.env` com suas configurações:

```env
# Obrigatório
TELEGRAM_TOKEN=seu_token_bot_aqui
PERPLEXITY_SESSION_TOKEN=seu_session_token_aqui

# Deploy
WEBHOOK_URL=https://seu-dominio.com/telegram

# Opcional
OPENAI_API_KEY=sua_chave_openai_para_whisper
ADMIN_USER_ID=seu_id_telegram
```

---

## Deploy com Docker

### 1. Instale Docker (se necessário)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Inicie os serviços

```bash
# Build e start
docker-compose up -d --build

# Verifique os logs
docker-compose logs -f

# Verifique status
docker-compose ps
```

### 3. Comandos úteis

```bash
# Parar serviços
docker-compose down

# Reiniciar
docker-compose restart

# Atualizar após mudanças
docker-compose up -d --build

# Ver logs de um serviço específico
docker-compose logs -f mcp-server
docker-compose logs -f telegram-bot
docker-compose logs -f whatsapp-bot

# Acessar shell de um container
docker-compose exec mcp-server bash
```

---

## Deploy Manual

### 1. Instale dependências Python

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Instale dependências Node.js

```bash
npm install
```

### 3. Inicie os serviços com PM2

```bash
# Instale PM2 globalmente
npm install -g pm2

# Inicie todos os serviços
pm2 start ecosystem.config.js

# Salve a configuração
pm2 save
pm2 startup

# Monitore
pm2 monit
pm2 logs
```

---

## Configuração do Telegram

### 1. Crie um bot no BotFather

1. Abra o Telegram e procure por **@BotFather**
2. Envie `/newbot`
3. Siga as instruções para nomear seu bot
4. Copie o **token** fornecido
5. Cole no `.env` como `TELEGRAM_TOKEN`

### 2. Configure os comandos do menu

No BotFather:
```
/setcommands

start - 🏠 Menu Principal
modelos - 🤖 Escolher Modelo AI
busca - 🔍 Modo de Busca (Focus)
normal - 💬 Conversa Normal
config - ⚙️ Configurações
ajuda - ❓ Guia de Uso
```

### 3. Configure o Webhook

Para produção (com domínio):
```bash
curl -X POST "https://api.telegram.org/bot<SEU_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://seu-dominio.com/telegram"}'
```

Para desenvolvimento (polling):
- Deixe `WEBHOOK_URL=` vazio no `.env`
- O bot usará polling automaticamente

---

## Configuração do WhatsApp

### 1. Primeira execução

O WhatsApp bot usa **Baileys** e requer autenticação via QR code na primeira execução:

```bash
# Execute manualmente para ver o QR code
node src/whatsapp_bot.js
```

### 2. Escaneie o QR code

1. Abra o WhatsApp no celular
2. Vá em **Configurações > Dispositivos Conectados**
3. Escaneie o QR code exibido no terminal
4. A sessão será salva em `data/perplexo-session/`

### 3. Sessão persistente

Após a primeira autenticação, o bot manterá a sessão. O QR code só será necessário novamente se:
- Você desconectar do WhatsApp Web no celular
- Deletar a pasta `data/perplexo-session/`
- O token expirar

---

## Obtenção do Session Token Perplexity

O session token é necessário para o scraper funcionar:

### Método 1: Via DevTools (Browser)

1. Acesse [perplexity.ai](https://perplexity.ai) e faça login
2. Abra o DevTools (F12)
3. Vá em **Application > Cookies > https://www.perplexity.ai**
4. Procure por `__Secure-next-auth.session-token`
5. Copie o valor e cole no `.env`

### Método 2: Via Extensão

1. Instale a extensão "EditThisCookie" ou similar
2. Acesse perplexity.ai
3. Exporte os cookies
4. Extraia o valor de `__Secure-next-auth.session-token`

### ⚠️ Importante

- O token expira aproximadamente a cada **30 dias**
- Quando expirar, o bot funcionará em modo simulação
- Renove o token periodicamente

---

## Configuração de SSL

### Usando Let's Encrypt (Certbot)

```bash
# Instale o Certbot
sudo apt install certbot

# Obtenha o certificado
sudo certbot certonly --standalone -d seu-dominio.com

# Copie para o projeto
sudo cp /etc/letsencrypt/live/seu-dominio.com/fullchain.pem ./data/ssl/
sudo cp /etc/letsencrypt/live/seu-dominio.com/privkey.pem ./data/ssl/

# Configure permissões
sudo chmod 644 ./data/ssl/*.pem
```

### Auto-renovação

```bash
# Teste a renovação
sudo certbot renew --dry-run

# Adicione ao crontab
sudo crontab -e

# Adicione esta lina (renova a cada 2 meses)
0 0 1 */2 * certbot renew --quiet && cp /etc/letsencrypt/live/seu-dominio.com/*.pem /path/to/perplexo/data/ssl/
```

---

## Troubleshooting

### Bot do Telegram não responde

```bash
# Verifique o webhook
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Delete e recrie o webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://seu-dominio.com/telegram"

# Verifique logs
docker-compose logs -f telegram-bot
```

### WhatsApp desconecta frequentemente

```bash
# Verifique se a sessão existe
ls -la data/perplexo-session/

# Delete e reconecte
rm -rf data/perplexo-session/
docker-compose restart whatsapp-bot
```

### Erro "Rate limit exceeded"

- O usuário atingiu o limite de requisições
- Configure `RATE_LIMIT_MESSAGES` e `RATE_LIMIT_WINDOW` no `.env`
- Padrão: 20 mensagens por hora

### MCP Server não responde

```bash
# Verifique se está rodando
curl http://localhost:5000/health

# Reinicie
docker-compose restart mcp-server

# Verifique logs
docker-compose logs -f mcp-server
```

### Erro de permissão no SQLite

```bash
# Corrija permissões
chmod 755 data/
chmod 644 data/*.db

# Ou recrie o container
docker-compose down
docker-compose up -d
```

---

## Atualização

```bash
# Pull das mudanças
git pull

# Rebuild e restart
docker-compose down
docker-compose up -d --build

# Ou com PM2
pm2 restart all
```

---

## Backup

```bash
# Backup do banco de dados
cp data/perplexo.db backup/perplexo-$(date +%Y%m%d).db

# Backup da sessão WhatsApp
tar -czf backup/whatsapp-session-$(date +%Y%m%d).tar.gz data/perplexo-session/

# Backup completo
tar -czf backup/perplexo-full-$(date +%Y%m%d).tar.gz data/ logs/ .env
```

---

## Suporte

Para problemas ou dúvidas:
1. Verifique os logs: `docker-compose logs` ou `pm2 logs`
2. Confira as variáveis de ambiente no `.env`
3. Verifique se as portas não estão em uso: `netstat -tlnp`