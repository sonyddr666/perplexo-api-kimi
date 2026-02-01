/**
 * Perplexo Bot - WhatsApp Bot Implementation
 * Uses Baileys library for WhatsApp Web integration
 */

const { 
  default: makeWASocket, 
  DisconnectReason, 
  useMultiFileAuthState,
  downloadMediaMessage
} = require('@whiskeysockets/baileys');
const axios = require('axios');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

// Config
const MCP_API = process.env.MCP_API_URL || 'http://127.0.0.1:5000';
const SESSION_NAME = process.env.WHATSAPP_SESSION_NAME || 'perplexo-session';
const ADMIN_NUMBER = process.env.ADMIN_WHATSAPP_NUMBER || '';

// Logger
const logger = pino({ 
  level: process.env.LOG_LEVEL || 'info',
  transport: {
    target: 'pino-pretty',
    options: { colorize: true }
  }
});

// User preferences cache (in production, use database)
const userPreferences = new Map();

// Models and Focuses
const MODELS = [
  { id: 'sonar', name: '⚡ Sonar', desc: 'Rápido (10x), 128K' },
  { id: 'sonar-pro', name: '🔥 Sonar Pro', desc: '2x retrieval, 200K' },
  { id: 'gpt-5.2', name: '🧠 GPT-5.2', desc: 'OpenAI, coding' },
  { id: 'reasoning-pro', name: '🤔 Reasoning Pro', desc: 'Lógica stepwise' },
  { id: 'deep-research', name: '📊 Deep Research', desc: 'Pesquisa máxima' }
];

const FOCUSES = [
  { id: 'web', name: '🌐 Web', desc: 'Busca geral' },
  { id: 'academic', name: '🎓 Academic', desc: 'Papers científicos' },
  { id: 'writing', name: '✍️ Writing', desc: 'Conteúdo criativo' },
  { id: 'video', name: '🎥 Video', desc: 'YouTube/Vídeos' },
  { id: 'social', name: '💬 Social', desc: 'X/Reddit' },
  { id: 'math', name: '🔢 Math', desc: 'Matemática' },
  { id: 'wolfram', name: '🧮 Wolfram', desc: 'Cálculos avançados' }
];

/**
 * Get or create user configuration
 */
async function getUserConfig(userId) {
  if (userPreferences.has(userId)) {
    return userPreferences.get(userId);
  }
  
  try {
    const response = await axios.get(`${MCP_API}/config/${userId}`, {
      params: { platform: 'whatsapp' }
    });
    const config = response.data;
    userPreferences.set(userId, config);
    return config;
  } catch (error) {
    logger.warn(`Failed to get config for ${userId}, using defaults`);
    return {
      model: 'sonar',
      focus: 'web',
      mode: 'busca',
      reasoning: false,
      return_citations: true,
      return_images: false
    };
  }
}

/**
 * Update user configuration
 */
async function updateUserConfig(userId, config) {
  userPreferences.set(userId, config);
  
  try {
    await axios.post(`${MCP_API}/config/${userId}`, config, {
      params: { platform: 'whatsapp' }
    });
  } catch (error) {
    logger.error(`Failed to update config for ${userId}:`, error.message);
  }
}

/**
 * Format menu text
 */
function formatMenu(config) {
  return `🌀 *Perplexo Bot* - Perplexity AI 2026

*Configuração Atual:*
🤖 Modelo: \`${config.model}\`
🔍 Focus: \`${config.focus}\`
💬 Modo: \`${config.mode}\`

*Comandos disponíveis:*
• *!menu* - Mostrar este menu
• *!modelo* - Escolher modelo AI
• *!busca* - Modo de busca (Focus)
• *!normal* - Conversa casual
• *!config* - Configurações
• *!ajuda* - Guia de uso

_Envie sua pergunta diretamente!_`;
}

/**
 * Format models menu
 */
function formatModelsMenu(currentModel) {
  let text = '🤖 *Escolher Modelo AI*\n\n';
  
  MODELS.forEach(m => {
    const marker = m.id === currentModel ? '✅' : '○';
    text += `${marker} *${m.name}*\n   _${m.desc}_\n\n`;
  });
  
  text += '\n*Responda com o número do modelo:*\n';
  MODELS.forEach((m, i) => {
    text += `${i + 1}. ${m.name.replace(/[⚡🔥🧠🤔📊]/g, '').trim()}\n`;
  });
  
  return text;
}

/**
 * Format focus menu
 */
function formatFocusMenu(currentFocus) {
  let text = '🔍 *Modo de Busca (Focus)*\n\n';
  
  FOCUSES.forEach(f => {
    const marker = f.id === currentFocus ? '✅' : '○';
    text += `${marker} *${f.name}* - ${f.desc}\n`;
  });
  
  text += '\n*Responda com o número do focus:*\n';
  FOCUSES.forEach((f, i) => {
    text += `${i + 1}. ${f.name.replace(/[🌐🎓✍️🎥💬🔢🧮]/g, '').trim()}\n`;
  });
  
  return text;
}

/**
 * Format config menu
 */
function formatConfigMenu(config) {
  return `⚙️ *Configurações*

*Modelo Atual:* \`${config.model}\`
*Focus Atual:* \`${config.focus}\`
*Modo:* \`${config.mode}\`

*Opções:*
${config.reasoning ? '🟢' : '🔴'} Reasoning
${config.return_citations ? '🟢' : '🔴'} Citações
${config.return_images ? '🟢' : '🔴'} Imagens

*Comandos:*
• *!reasoning* - Alternar reasoning
• *!citations* - Alternar citações
• *!imagens* - Alternar imagens`;
}

/**
 * Format help text
 */
function formatHelp() {
  return `❓ *Guia de Uso do Perplexo Bot*

*Comandos:*
• *!menu* - Menu principal
• *!modelo* - Escolher modelo AI
• *!busca* - Modo de busca (Focus)
• *!normal* - Conversa casual
• *!config* - Configurações
• *!ajuda* - Este guia

*Recursos:*
• Envie texto para perguntas
• Envie imagens para análise
• Envie arquivos .txt para resumir
• Envie áudio para transcrição

*Modelos:*
⚡ Sonar - Rápido, Q&A
🔥 Sonar Pro - Análises detalhadas
🧠 GPT-5.2 - Coding
🤔 Reasoning Pro - Lógica
📊 Deep Research - Pesquisa`;
}

/**
 * Process text query
 */
async function processQuery(sock, sender, text, config, userId) {
  await sock.sendMessage(sender, { text: '🤔 Processando...' });
  
  try {
    const response = await axios.post(`${MCP_API}/search`, {
      query: text,
      model: config.model,
      focus: config.focus,
      enable_reasoning: config.reasoning,
      return_citations: config.return_citations,
      return_images: config.return_images,
      user_id: userId,
      platform: 'whatsapp'
    }, { timeout: 60000 });
    
    const data = response.data;
    let answer = data.answer || data.text;
    
    // Add citations
    if (config.return_citations && data.citations && data.citations.length > 0) {
      answer += '\n\n📚 *Fontes:*\n';
      data.citations.slice(0, 5).forEach((cite, i) => {
        const title = cite.title || 'Link';
        const url = cite.url || '';
        answer += `${i + 1}. ${title}\n`;
        if (url) answer += `   ${url}\n`;
      });
    }
    
    // Add metadata
    answer += `\n_🤖 ${data.model_used || config.model} | 🔍 ${data.focus_mode || config.focus}_`;
    
    // Split long messages (WhatsApp limit ~4096)
    const chunks = answer.match(/[\s\S]{1,4000}/g) || [answer];
    
    for (const chunk of chunks) {
      await sock.sendMessage(sender, { text: chunk });
    }
    
    // Send images if any
    if (config.return_images && data.images && data.images.length > 0) {
      for (const imgUrl of data.images.slice(0, 3)) {
        try {
          await sock.sendMessage(sender, { 
            image: { url: imgUrl },
            caption: '🖼️ Imagem relacionada'
          });
        } catch (e) {
          logger.warn('Failed to send image:', e.message);
        }
      }
    }
    
  } catch (error) {
    logger.error('Query error:', error.message);
    
    if (error.response?.status === 429) {
      const data = error.response.data;
      await sock.sendMessage(sender, { 
        text: `⏱️ *Rate Limit Excedido*\n\nVocê atingiu o limite de ${data.limit || 20} requisições por hora.` 
      });
    } else {
      await sock.sendMessage(sender, { 
        text: '❌ Erro ao processar. Tente novamente mais tarde.' 
      });
    }
  }
}

/**
 * Process image
 */
async function processImage(sock, sender, imageBuffer, caption, config, userId) {
  await sock.sendMessage(sender, { text: '🖼️ Analisando imagem...' });
  
  try {
    const imageB64 = imageBuffer.toString('base64');
    
    const response = await axios.post(`${MCP_API}/vision`, {
      query: caption || 'O que você vê nesta imagem?',
      image_base64: imageB64,
      model: config.model,
      user_id: userId,
      platform: 'whatsapp'
    }, { timeout: 90000 });
    
    const data = response.data;
    const answer = data.text || data.answer || 'Não foi possível analisar a imagem.';
    
    await sock.sendMessage(sender, { text: answer });
    
  } catch (error) {
    logger.error('Image processing error:', error.message);
    await sock.sendMessage(sender, { 
      text: '❌ Erro ao analisar imagem. Tente novamente.' 
    });
  }
}

/**
 * Process document
 */
async function processDocument(sock, sender, documentBuffer, fileName, config, userId) {
  if (!fileName.endsWith('.txt')) {
    await sock.sendMessage(sender, { 
      text: '⚠️ Por enquanto só aceito arquivos .txt' 
    });
    return;
  }
  
  await sock.sendMessage(sender, { text: '📄 Processando arquivo...' });
  
  try {
    const textContent = documentBuffer.toString('utf-8');
    const truncated = textContent.length > 10000 
      ? textContent.substring(0, 10000) + '\n[...truncado]' 
      : textContent;
    
    const response = await axios.post(`${MCP_API}/search`, {
      query: `Resuma o seguinte texto:\n\n${truncated}`,
      model: config.model,
      focus: 'writing',
      return_citations: false,
      user_id: userId,
      platform: 'whatsapp'
    }, { timeout: 90000 });
    
    const data = response.data;
    const answer = `📄 *Resumo de ${fileName}:*\n\n${data.answer || data.text}`;
    
    // Split if too long
    const chunks = answer.match(/[\s\S]{1,4000}/g) || [answer];
    for (const chunk of chunks) {
      await sock.sendMessage(sender, { text: chunk });
    }
    
  } catch (error) {
    logger.error('Document processing error:', error.message);
    await sock.sendMessage(sender, { 
      text: '❌ Erro ao processar arquivo.' 
    });
  }
}

/**
 * Process audio/voice
 */
async function processAudio(sock, sender, audioBuffer, config, userId) {
  await sock.sendMessage(sender, { text: '🎤 Transcrevendo áudio...' });
  
  try {
    const audioB64 = audioBuffer.toString('base64');
    
    const response = await axios.post(`${MCP_API}/transcribe`, {
      audio_base64: audioB64,
      language: 'pt',
      user_id: userId,
      platform: 'whatsapp'
    }, { timeout: 60000 });
    
    const data = response.data;
    const transcribedText = data.text;
    
    if (!transcribedText) {
      await sock.sendMessage(sender, { 
        text: '❌ Não consegui entender o áudio.' 
      });
      return;
    }
    
    await sock.sendMessage(sender, { 
      text: `🎤 *Transcrição:*\n_${transcribedText}_\n\n_Processando..._` 
    });
    
    // Process transcribed text as query
    await processQuery(sock, sender, transcribedText, config, userId);
    
  } catch (error) {
    logger.error('Audio processing error:', error.message);
    await sock.sendMessage(sender, { 
      text: '❌ Erro ao processar áudio. Verifique se a transcrição está configurada.' 
    });
  }
}

/**
 * Handle incoming messages
 */
async function handleMessage(sock, msg) {
  try {
    // Ignore messages from self
    if (msg.key.fromMe) return;
    
    const sender = msg.key.remoteJid;
    const userId = parseInt(sender.replace(/[^0-9]/g, '').substring(0, 10)) || 0;
    
    // Get user config
    const config = await getUserConfig(userId);
    
    // Handle different message types
    const messageType = Object.keys(msg.message || {})[0];
    
    // Text message
    if (messageType === 'conversation' || messageType === 'extendedTextMessage') {
      const text = msg.message.conversation || 
                   msg.message.extendedTextMessage?.text || '';
      
      const cmd = text.toLowerCase().trim();
      
      // Command handling
      if (cmd === '!menu' || cmd === '!start') {
        await sock.sendMessage(sender, { text: formatMenu(config) });
        return;
      }
      
      if (cmd === '!modelo' || cmd === '!modelos') {
        await sock.sendMessage(sender, { text: formatModelsMenu(config.model) });
        // Set state to expect model selection
        userPreferences.set(`${userId}_state`, 'selecting_model');
        return;
      }
      
      if (cmd === '!busca') {
        await sock.sendMessage(sender, { text: formatFocusMenu(config.focus) });
        userPreferences.set(`${userId}_state`, 'selecting_focus');
        return;
      }
      
      if (cmd === '!normal') {
        config.mode = 'normal';
        config.return_citations = false;
        await updateUserConfig(userId, config);
        await sock.sendMessage(sender, { 
          text: '💬 *Modo Normal ativado*\n\nAgora respondo sem citações.' 
        });
        return;
      }
      
      if (cmd === '!config') {
        await sock.sendMessage(sender, { text: formatConfigMenu(config) });
        return;
      }
      
      if (cmd === '!ajuda' || cmd === '!help') {
        await sock.sendMessage(sender, { text: formatHelp() });
        return;
      }
      
      if (cmd === '!reasoning') {
        config.reasoning = !config.reasoning;
        await updateUserConfig(userId, config);
        await sock.sendMessage(sender, { 
          text: `🧠 Reasoning ${config.reasoning ? 'ativado' : 'desativado'}!` 
        });
        return;
      }
      
      if (cmd === '!citations') {
        config.return_citations = !config.return_citations;
        await updateUserConfig(userId, config);
        await sock.sendMessage(sender, { 
          text: `📚 Citações ${config.return_citations ? 'ativadas' : 'desativadas'}!` 
        });
        return;
      }
      
      if (cmd === '!imagens') {
        config.return_images = !config.return_images;
        await updateUserConfig(userId, config);
        await sock.sendMessage(sender, { 
          text: `🖼️ Imagens ${config.return_images ? 'ativadas' : 'desativadas'}!` 
        });
        return;
      }
      
      // Check for state-based input
      const state = userPreferences.get(`${userId}_state`);
      
      if (state === 'selecting_model') {
        const num = parseInt(text);
        if (num >= 1 && num <= MODELS.length) {
          config.model = MODELS[num - 1].id;
          config.mode = 'busca';
          await updateUserConfig(userId, config);
          await sock.sendMessage(sender, { 
            text: `✅ Modelo alterado para *${MODELS[num - 1].name}*` 
          });
        } else {
          await sock.sendMessage(sender, { 
            text: '❌ Número inválido. Envie !modelo para ver opções.' 
          });
        }
        userPreferences.delete(`${userId}_state`);
        return;
      }
      
      if (state === 'selecting_focus') {
        const num = parseInt(text);
        if (num >= 1 && num <= FOCUSES.length) {
          config.focus = FOCUSES[num - 1].id;
          config.mode = 'busca';
          await updateUserConfig(userId, config);
          await sock.sendMessage(sender, { 
            text: `✅ Focus alterado para *${FOCUSES[num - 1].name}*` 
          });
        } else {
          await sock.sendMessage(sender, { 
            text: '❌ Número inválido. Envie !busca para ver opções.' 
          });
        }
        userPreferences.delete(`${userId}_state`);
        return;
      }
      
      // Regular query
      await processQuery(sock, sender, text, config, userId);
    }
    
    // Image message
    if (messageType === 'imageMessage') {
      const caption = msg.message.imageMessage.caption || '';
      const buffer = await downloadMediaMessage(msg, 'buffer', {});
      await processImage(sock, sender, buffer, caption, config, userId);
    }
    
    // Document message
    if (messageType === 'documentMessage') {
      const fileName = msg.message.documentMessage.fileName || 'document';
      const buffer = await downloadMediaMessage(msg, 'buffer', {});
      await processDocument(sock, sender, buffer, fileName, config, userId);
    }
    
    // Audio/Voice message
    if (messageType === 'audioMessage' || messageType === 'pttMessage') {
      const buffer = await downloadMediaMessage(msg, 'buffer', {});
      await processAudio(sock, sender, buffer, config, userId);
    }
    
  } catch (error) {
    logger.error('Message handling error:', error);
  }
}

/**
 * Connect to WhatsApp
 */
async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(
    path.join(__dirname, '..', 'data', SESSION_NAME)
  );
  
  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: true,
    logger: pino({ level: 'silent' }),
    browser: ['Perplexo Bot', 'Chrome', '1.0']
  });
  
  // Save credentials
  sock.ev.on('creds.update', saveCreds);
  
  // Handle messages
  sock.ev.on('messages.upsert', async ({ messages }) => {
    for (const msg of messages) {
      await handleMessage(sock, msg);
    }
  });
  
  // Handle connection updates
  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect } = update;
    
    if (connection === 'close') {
      const shouldReconnect = 
        lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
      
      logger.info('Connection closed, reconnecting:', shouldReconnect);
      
      if (shouldReconnect) {
        connectToWhatsApp();
      }
    } else if (connection === 'open') {
      logger.info('✅ WhatsApp connected!');
      
      // Notify admin
      if (ADMIN_NUMBER) {
        sock.sendMessage(ADMIN_NUMBER + '@s.whatsapp.net', {
          text: '🤖 Perplexo Bot iniciado e conectado!'
        }).catch(() => {});
      }
    }
  });
}

// Start
logger.info('🚀 Starting Perplexo WhatsApp Bot...');
connectToWhatsApp().catch(err => {
  logger.error('Failed to start:', err);
  process.exit(1);
});