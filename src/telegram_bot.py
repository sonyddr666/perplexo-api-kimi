"""
Perplexo Bot - Telegram Bot Implementation.
Provides a visual UI with inline keyboards, toggles, and support for images/voice.
"""

import os
import base64
import logging
from io import BytesIO
from typing import Optional

import httpx
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
MCP_API = os.getenv("MCP_API_URL", "http://127.0.0.1:5000")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Model and Focus definitions
MODELS = [
    ('sonar', '⚡ Sonar', 'Rápido (10x), 128K'),
    ('sonar-pro', '🔥 Sonar Pro', '2x retrieval, 200K'),
    ('gpt-5.2', '🧠 GPT-5.2', 'OpenAI, coding'),
    ('reasoning-pro', '🤔 Reasoning Pro', 'Lógica stepwise'),
    ('deep-research', '📊 Deep Research', 'Pesquisa máxima')
]

FOCUSES = [
    ('web', '🌐 Web', 'Busca geral'),
    ('academic', '🎓 Academic', 'Papers científicos'),
    ('writing', '✍️ Writing', 'Conteúdo criativo'),
    ('video', '🎥 Video', 'YouTube/Vídeos'),
    ('social', '💬 Social', 'X/Reddit'),
    ('math', '🔢 Math', 'Matemática'),
    ('wolfram', '🧮 Wolfram', 'Cálculos avançados')
]


# ==================== SETUP ====================

async def post_init(application: Application):
    """Register commands in Telegram menu."""
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


# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal /start"""
    user_id = update.effective_user.id
    config = await get_user_config(user_id)
    
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


async def cmd_modelos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /modelos - Seletor visual de modelos"""
    user_id = update.effective_user.id
    config = await get_user_config(user_id)
    current_model = config['model']
    
    keyboard = []
    for model_id, emoji_name, description in MODELS:
        prefix = "✅ " if model_id == current_model else ""
        button_text = f"{prefix}{emoji_name}"
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f'set_model_{model_id}'
        )])
    
    keyboard.append([InlineKeyboardButton("« Voltar", callback_data='back_main')])
    
    text = "🤖 **Escolher Modelo AI**\n\n"
    for model_id, emoji_name, description in MODELS:
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


async def cmd_busca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /busca - Seletor de Focus modes"""
    user_id = update.effective_user.id
    config = await get_user_config(user_id)
    current_focus = config['focus']
    
    keyboard = []
    for focus_id, emoji_name, description in FOCUSES:
        prefix = "✅ " if focus_id == current_focus else ""
        button_text = f"{prefix}{emoji_name}"
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f'set_focus_{focus_id}'
        )])
    
    keyboard.append([InlineKeyboardButton("« Voltar", callback_data='back_main')])
    
    text = "🔍 **Modo de Busca (Focus)**\n\n"
    for focus_id, emoji_name, description in FOCUSES:
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


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /config - Painel de controle com toggles"""
    user_id = update.effective_user.id
    config = await get_user_config(user_id)
    
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
        f"⚙️ **Configurações**\n\n"
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


async def cmd_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /normal - Modo conversa casual"""
    user_id = update.effective_user.id
    await update_user_config(user_id, {
        'mode': 'normal',
        'return_citations': False
    })
    
    text = (
        "💬 **Modo Normal ativado**\n\n"
        "Agora respondo sem citações, como uma conversa casual.\n"
        "Use /busca para voltar ao modo pesquisa."
    )
    
    if update.callback_query:
        await update.callback_query.answer("Modo normal ativado!")
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')


async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ajuda - Guia de uso"""
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
        "• Envie arquivos .txt para resumir\n"
        "• Envie mensagens de voz para transcrição\n\n"
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


# ==================== CALLBACK HANDLER ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para todos os botões inline"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Navegação
    if data == 'back_main':
        await query.message.delete()
        # Create a mock update to call start
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
        config = await get_user_config(user_id)
        config['model'] = model
        config['mode'] = 'busca'
        await update_user_config(user_id, config)
        
        await query.answer(f"✅ Modelo {model.upper()} selecionado!")
        await cmd_modelos(update, context)
    
    # Seleção de focus
    elif data.startswith('set_focus_'):
        focus = data.replace('set_focus_', '')
        config = await get_user_config(user_id)
        config['focus'] = focus
        config['mode'] = 'busca'
        await update_user_config(user_id, config)
        
        await query.answer(f"✅ Focus {focus.upper()} selecionado!")
        await cmd_busca(update, context)
    
    # Toggles
    elif data.startswith('toggle_'):
        setting = data.replace('toggle_', '')
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{MCP_API}/config/{user_id}/toggle/{setting}",
                    params={"platform": "telegram"}
                )
                result = response.json()
                
                if result.get('success'):
                    status = "ativado" if result['value'] else "desativado"
                    await query.answer(f"{setting.replace('_', ' ').title()} {status}!")
                    await cmd_config(update, context)
        except Exception as e:
            logger.error(f"Error toggling setting: {e}")
            await query.answer("❌ Erro ao alterar configuração")


# ==================== MESSAGE HANDLERS ====================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens de texto"""
    user_id = update.effective_user.id
    user_query = update.message.text
    config = await get_user_config(user_id)
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "query": user_query,
                "model": config['model'],
                "focus": config['focus'],
                "enable_reasoning": config['reasoning'],
                "return_citations": config['return_citations'],
                "return_images": config['return_images'],
                "user_id": user_id,
                "platform": "telegram"
            }
            
            response = await client.post(f"{MCP_API}/search", json=payload)
            
            if response.status_code == 429:
                data = response.json()
                await update.message.reply_text(
                    f"⏱️ **Rate Limit Excedido**\n\n"
                    f"Você atingiu o limite de {data.get('limit', 20)} requisições por hora.\n"
                    f"Reset em: {data.get('reset_time', 'em breve')}",
                    parse_mode='Markdown'
                )
                return
            
            response.raise_for_status()
            data = response.json()
        
        answer = data['answer']
        
        # Adiciona citações
        if config['return_citations'] and data.get('citations'):
            answer += "\n\n📚 **Fontes:**\n"
            for i, cite in enumerate(data['citations'][:5], 1):
                title = cite.get('title', 'Link')
                url = cite.get('url', '')
                answer += f"{i}. [{title}]({url})\n"
        
        # Badge de metadados
        answer += f"\n_🤖 {data.get('model_used', config['model'])} | 🔍 {data.get('focus_mode', config['focus'])}_"
        
        # Verifica se resposta é muito longa
        if len(answer) > 4000:
            # Telegram limit is 4096, send in parts
            parts = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
            for i, part in enumerate(parts):
                if i == 0:
                    await update.message.reply_text(
                        part,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=part,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
        else:
            await update.message.reply_text(
                answer,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        
        # Envia imagens se retornadas
        if config['return_images'] and data.get('images'):
            for img_url in data['images'][:3]:
                try:
                    await update.message.reply_photo(photo=img_url)
                except Exception as e:
                    logger.warning(f"Erro ao enviar imagem: {e}")
        
    except httpx.TimeoutException:
        await update.message.reply_text(
            "⏱️ Timeout. Tente um modelo mais rápido (/modelos)",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Erro: {e}")
        await update.message.reply_text(
            "❌ Erro ao processar. Use /config para verificar suas configurações.",
            parse_mode='Markdown'
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa imagens enviadas pelo usuário"""
    user_id = update.effective_user.id
    config = await get_user_config(user_id)
    
    caption = update.message.caption or "O que você vê nesta imagem?"
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        # Download da imagem
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        photo_b64 = base64.b64encode(photo_bytes).decode()
        
        # Chama MCP API com imagem
        async with httpx.AsyncClient(timeout=90.0) as client:
            payload = {
                "query": caption,
                "model": config['model'],
                "image_base64": photo_b64,
                "user_id": user_id,
                "platform": "telegram"
            }
            
            response = await client.post(f"{MCP_API}/vision", json=payload)
            response.raise_for_status()
            data = response.json()
        
        answer = data.get('text', data.get('answer', 'Não foi possível analisar a imagem.'))
        await update.message.reply_text(answer, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        await update.message.reply_text(
            "❌ Erro ao analisar imagem. Tente novamente ou use outro modelo.",
            parse_mode='Markdown'
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa arquivos de texto"""
    user_id = update.effective_user.id
    config = await get_user_config(user_id)
    
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
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
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
                "return_citations": False,
                "user_id": user_id,
                "platform": "telegram"
            }
            
            response = await client.post(f"{MCP_API}/search", json=payload)
            response.raise_for_status()
            data = response.json()
        
        answer = f"📄 **Resumo de {file_name}:**\n\n{data['answer']}"
        
        # Truncar se necessário
        if len(answer) > 4000:
            answer = answer[:3997] + "..."
        
        await update.message.reply_text(answer, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Erro ao processar documento: {e}")
        await update.message.reply_text(
            "❌ Erro ao processar arquivo. Verifique se é UTF-8.",
            parse_mode='Markdown'
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens de voz"""
    user_id = update.effective_user.id
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        # Download do áudio
        voice_file = await update.message.voice.get_file()
        voice_bytes = await voice_file.download_as_bytearray()
        voice_b64 = base64.b64encode(voice_bytes).decode()
        
        # Transcreve usando MCP API (Whisper)
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "audio_base64": voice_b64,
                "language": "pt",
                "user_id": user_id,
                "platform": "telegram"
            }
            
            response = await client.post(f"{MCP_API}/transcribe", json=payload)
            response.raise_for_status()
            data = response.json()
        
        transcribed_text = data.get('text', '')
        
        if not transcribed_text:
            await update.message.reply_text(
                "❌ Não consegui entender o áudio. Tente novamente.",
                parse_mode='Markdown'
            )
            return
        
        # Envia transcrição
        await update.message.reply_text(
            f"🎤 **Transcrição:**\n_{transcribed_text}_\n\n_Processando..._",
            parse_mode='Markdown'
        )
        
        # Processa como mensagem de texto
        update.message.text = transcribed_text
        await handle_text_message(update, context)
        
    except Exception as e:
        logger.error(f"Erro ao processar voz: {e}")
        await update.message.reply_text(
            "❌ Erro ao processar mensagem de voz.",
            parse_mode='Markdown'
        )


# ==================== HELPER FUNCTIONS ====================

async def get_user_config(user_id: int) -> dict:
    """Get user configuration from MCP API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MCP_API}/config/{user_id}",
                params={"platform": "telegram"}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error getting user config: {e}")
        # Return defaults
        return {
            'model': 'sonar',
            'focus': 'web',
            'mode': 'busca',
            'reasoning': False,
            'return_citations': True,
            'return_images': True
        }


async def update_user_config(user_id: int, config: dict):
    """Update user configuration via MCP API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_API}/config/{user_id}",
                params={"platform": "telegram"},
                json=config
            )
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Error updating user config: {e}")


# ==================== MAIN ====================

def main():
    """Inicia o bot"""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN não configurado!")
        return
    
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
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Webhook ou Polling
    if WEBHOOK_URL:
        port = int(os.getenv("TELEGRAM_PORT", "8000"))
        logger.info(f"🚀 Iniciando webhook em {WEBHOOK_URL}")
        app.run_webhook(
            listen="127.0.0.1",
            port=port,
            webhook_url=WEBHOOK_URL,
            url_path="/telegram"
        )
    else:
        logger.info("🚀 Rodando em modo polling (desenvolvimento)")
        app.run_polling()


if __name__ == "__main__":
    main()