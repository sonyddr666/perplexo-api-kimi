module.exports = {
  apps: [
    {
      name: 'perplexo-mcp',
      script: 'src/mcp_server.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production'
      },
      log_file: 'logs/mcp.log',
      out_file: 'logs/mcp.out.log',
      error_file: 'logs/mcp.error.log',
      merge_logs: true,
      time: true
    },
    {
      name: 'perplexo-telegram',
      script: 'src/telegram_bot.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        NODE_ENV: 'production'
      },
      log_file: 'logs/telegram.log',
      out_file: 'logs/telegram.out.log',
      error_file: 'logs/telegram.error.log',
      merge_logs: true,
      time: true
    },
    {
      name: 'perplexo-whatsapp',
      script: 'src/whatsapp_bot.js',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '400M',
      env: {
        NODE_ENV: 'production'
      },
      log_file: 'logs/whatsapp.log',
      out_file: 'logs/whatsapp.out.log',
      error_file: 'logs/whatsapp.error.log',
      merge_logs: true,
      time: true
    }
  ]
};
