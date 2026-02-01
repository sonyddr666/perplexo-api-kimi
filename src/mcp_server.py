"""
MCP Server - API wrapper for Perplexity scraper.
Provides HTTP endpoints for the Telegram and WhatsApp bots.
"""

import os
import base64
import tempfile
import time
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
from waitress import serve

from scraper import PerplexoScraper, PerplexityModel, FocusMode
from database import Database

app = Flask(__name__)
CORS(app)

# Initialize components
db = Database(os.getenv("DATABASE_PATH", "data/perplexo.db"))
scraper = PerplexoScraper(
    session_token=os.getenv("PERPLEXITY_SESSION_TOKEN"),
    api_key=os.getenv("PERPLEXITY_API_KEY")
)

# Rate limiting config
RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "20"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "scraper_available": scraper.is_available(),
        "timestamp": datetime.now().isoformat()
    })


@app.route('/models', methods=['GET'])
def list_models():
    """List available models and focus modes."""
    return jsonify({
        "models": scraper.list_models(),
        "focus_modes": scraper.list_focus_modes()
    })


@app.route('/search', methods=['POST'])
def search():
    """
    Search endpoint.
    
    Request body:
    {
        "query": "string",
        "model": "sonar|sonar-pro|gpt-5.2|reasoning-pro|deep-research",
        "focus": "web|academic|writing|video|social|math|wolfram",
        "enable_reasoning": bool,
        "return_citations": bool,
        "return_images": bool,
        "user_id": int (optional),
        "platform": "telegram|whatsapp" (optional)
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        if not data or 'query' not in data:
            return jsonify({"error": "Missing required field: query"}), 400
        
        query = data['query']
        model = data.get('model', 'sonar')
        focus = data.get('focus', 'web')
        enable_reasoning = data.get('enable_reasoning', False)
        return_citations = data.get('return_citations', True)
        return_images = data.get('return_images', False)
        
        user_id = data.get('user_id')
        platform = data.get('platform', 'telegram')
        
        # Check rate limit if user_id provided
        if user_id:
            allowed, remaining, reset_time = db.check_rate_limit(
                user_id, platform, RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW
            )
            
            if not allowed:
                return jsonify({
                    "error": "Rate limit exceeded",
                    "reset_time": reset_time.isoformat(),
                    "limit": RATE_LIMIT_MESSAGES
                }), 429
        
        # Call scraper
        start_time = time.time()
        
        result = scraper.ask(
            query=query,
            model=model,
            focus=focus,
            enable_reasoning=enable_reasoning
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Log query
        if user_id:
            db.log_query(
                user_id=user_id,
                platform=platform,
                query=query,
                model=model,
                focus=focus,
                response_time_ms=response_time_ms,
                success='error' not in result
            )
        
        # Filter response based on preferences
        if not return_citations:
            result['citations'] = []
        
        if not return_images:
            result['images'] = []
        
        # Add metadata
        result['response_time_ms'] = response_time_ms
        result['timestamp'] = datetime.now().isoformat()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "text": "❌ Erro interno no servidor",
            "citations": [],
            "images": []
        }), 500


@app.route('/vision', methods=['POST'])
def vision():
    """
    Vision/image analysis endpoint.
    
    Request body:
    {
        "query": "string",
        "image_base64": "base64_encoded_image",
        "model": "sonar-pro" (optional),
        "user_id": int (optional),
        "platform": "telegram|whatsapp" (optional)
    }
    """
    try:
        data = request.json
        
        if not data or 'query' not in data or 'image_base64' not in data:
            return jsonify({
                "error": "Missing required fields: query, image_base64"
            }), 400
        
        query = data['query']
        image_b64 = data['image_base64']
        model = data.get('model', 'sonar-pro')
        
        user_id = data.get('user_id')
        platform = data.get('platform', 'telegram')
        
        # Check rate limit
        if user_id:
            allowed, remaining, reset_time = db.check_rate_limit(
                user_id, platform, RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW
            )
            
            if not allowed:
                return jsonify({
                    "error": "Rate limit exceeded",
                    "reset_time": reset_time.isoformat()
                }), 429
        
        # Save image temporarily
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(base64.b64decode(image_b64))
            tmp_path = tmp.name
        
        try:
            # Call scraper with image
            start_time = time.time()
            
            result = scraper.ask_with_image(
                query=query,
                image_path=tmp_path,
                model=model
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Log query
            if user_id:
                db.log_query(
                    user_id=user_id,
                    platform=platform,
                    query=f"[IMAGE] {query}",
                    model=model,
                    focus="vision",
                    response_time_ms=response_time_ms,
                    success='error' not in result
                )
            
            result['response_time_ms'] = response_time_ms
            result['timestamp'] = datetime.now().isoformat()
            
            return jsonify(result)
            
        finally:
            # Cleanup temp file
            import os
            os.unlink(tmp_path)
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "text": "❌ Erro ao processar imagem"
        }), 500


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Audio transcription endpoint using Whisper.
    
    Request body:
    {
        "audio_base64": "base64_encoded_audio",
        "language": "pt" (optional),
        "user_id": int (optional),
        "platform": "telegram|whatsapp" (optional)
    }
    """
    try:
        data = request.json
        
        if not data or 'audio_base64' not in data:
            return jsonify({"error": "Missing required field: audio_base64"}), 400
        
        audio_b64 = data['audio_base64']
        language = data.get('language', 'pt')
        
        # Save audio temporarily
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
            tmp.write(base64.b64decode(audio_b64))
            tmp_path = tmp.name
        
        try:
            # Use OpenAI Whisper for transcription
            import openai
            
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                return jsonify({
                    "error": "OpenAI API key not configured",
                    "text": "⚠️ Transcrição de áudio não disponível. Configure OPENAI_API_KEY."
                }), 503
            
            client = openai.OpenAI(api_key=openai_api_key)
            
            with open(tmp_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
            
            return jsonify({
                "text": transcript.text,
                "language": language,
                "timestamp": datetime.now().isoformat()
            })
            
        finally:
            import os
            os.unlink(tmp_path)
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "text": "❌ Erro ao transcrever áudio"
        }), 500


@app.route('/stats/<int:user_id>', methods=['GET'])
def get_user_stats(user_id: int):
    """Get statistics for a specific user."""
    platform = request.args.get('platform', 'telegram')
    stats = db.get_user_stats(user_id, platform)
    return jsonify(stats)


@app.route('/stats', methods=['GET'])
def get_global_stats():
    """Get global statistics (admin only)."""
    stats = db.get_global_stats()
    return jsonify(stats)


@app.route('/config/<int:user_id>', methods=['GET', 'POST'])
def user_config(user_id: int):
    """Get or update user configuration."""
    platform = request.args.get('platform', 'telegram')
    
    if request.method == 'GET':
        config = db.get_user_config(user_id, platform)
        return jsonify(config)
    
    elif request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        db.update_user_config(user_id, platform, data)
        return jsonify({"success": True, "config": data})


@app.route('/config/<int:user_id>/toggle/<setting>', methods=['POST'])
def toggle_setting(user_id: int, setting: str):
    """Toggle a boolean setting for a user."""
    platform = request.args.get('platform', 'telegram')
    
    try:
        new_value = db.toggle_setting(user_id, platform, setting)
        return jsonify({
            "success": True,
            "setting": setting,
            "value": new_value
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


def main():
    """Run the MCP server."""
    port = int(os.getenv("MCP_PORT", "5000"))
    host = os.getenv("MCP_HOST", "127.0.0.1")
    
    print(f"🚀 Perplexo MCP Server starting on {host}:{port}")
    print(f"📊 Database: {os.getenv('DATABASE_PATH', 'data/perplexo.db')}")
    print(f"🤖 Scraper available: {scraper.is_available()}")
    
    # Use waitress for production
    serve(app, host=host, port=port, threads=4)


if __name__ == '__main__':
    main()