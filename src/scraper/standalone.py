"""
Standalone Perplexity scraper implementation.
Uses web scraping to interact with Perplexity AI.
"""

import re
import json
import time
import uuid
from typing import Dict, Any, Optional, List
import requests
from .base import PerplexityScraperBase


class PerplexoScraper(PerplexityScraperBase):
    """
    Standalone Perplexity scraper.
    Implements web scraping to communicate with Perplexity AI.
    """
    
    def __init__(self, session_token: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__(session_token, api_key)
        self.session = requests.Session()
        self._setup_headers()
        self._ws_sid: Optional[str] = None
        self._last_answer: Optional[Dict[str, Any]] = None
    
    def _setup_headers(self):
        """Setup HTTP headers for requests."""
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.perplexity.ai/",
            "Origin": "https://www.perplexity.ai",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })
        
        if self.session_token:
            self.session.headers.update({
                "Cookie": f"__Secure-next-auth.session-token={self.session_token}"
            })
    
    def _get_ws_sid(self) -> str:
        """Get WebSocket session ID."""
        if self._ws_sid:
            return self._ws_sid
        
        try:
            response = self.session.get(
                "https://www.perplexity.ai/socket.io/?EIO=4&transport=polling"
            )
            
            # Parse the response to get SID
            # Format: <length>{"sid":"...","upgrades":["websocket"],"pingInterval":...,"pingTimeout":...}
            match = re.search(r'"sid":"([^"]+)"', response.text)
            if match:
                self._ws_sid = match.group(1)
                return self._ws_sid
            else:
                raise Exception("Could not extract SID from response")
                
        except Exception as e:
            print(f"Error getting WS SID: {e}")
            # Generate a fallback SID
            self._ws_sid = str(uuid.uuid4())
            return self._ws_sid
    
    def ask(self,
            query: str,
            model: str = "sonar",
            focus: str = "web",
            enable_reasoning: bool = False,
            **kwargs) -> Dict[str, Any]:
        """
        Send a query to Perplexity and get response.
        
        Args:
            query: The user's question
            model: Model to use (sonar, sonar-pro, gpt-5.2, etc.)
            focus: Focus mode (web, academic, writing, etc.)
            enable_reasoning: Enable step-by-step reasoning
            
        Returns:
            Dict with keys: 'text', 'citations', 'images', 'model_used', 'focus_mode'
        """
        try:
            # Get or create session
            ws_sid = self._get_ws_sid()
            
            # Prepare the request payload
            # This is a simplified version - actual implementation would need
            # to match Perplexity's internal API structure
            
            payload = {
                "query": query,
                "model": model,
                "focus": focus,
                "reasoning": enable_reasoning,
                "session_id": ws_sid,
                "timestamp": int(time.time() * 1000)
            }
            
            # Try to use the internal API endpoint
            # Note: This is a reverse-engineered approach and may break
            try:
                response = self.session.post(
                    "https://www.perplexity.ai/rest/ratelimit/search/ask",
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data, model, focus)
                    
            except requests.RequestException as e:
                print(f"API request failed: {e}")
            
            # Fallback: Return a structured response indicating the limitation
            return {
                "text": (
                    f"⚠️ **Modo Simulação**\n\n"
                    f"Sua pergunta: *{query}*\n\n"
                    f"Para respostas reais do Perplexity, configure um session_token válido "
                    f"no arquivo .env (obtenha em perplexity.ai → DevTools → Application → Cookies).\n\n"
                    f"**Configurações usadas:**\n"
                    f"• Modelo: `{model}`\n"
                    f"• Focus: `{focus}`\n"
                    f"• Reasoning: `{'Sim' if enable_reasoning else 'Não'}`"
                ),
                "citations": [],
                "images": [],
                "model_used": model,
                "focus_mode": focus,
                "simulated": True
            }
            
        except Exception as e:
            return {
                "text": f"❌ Erro ao processar: {str(e)}",
                "citations": [],
                "images": [],
                "model_used": model,
                "focus_mode": focus,
                "error": str(e)
            }
    
    def _parse_response(self, data: Dict[str, Any], model: str, focus: str) -> Dict[str, Any]:
        """Parse the API response into a standardized format."""
        # Extract text
        text = data.get("text", "")
        if not text and "answer" in data:
            text = data["answer"]
        
        # Extract citations
        citations = []
        if "citations" in data:
            citations = data["citations"]
        elif "sources" in data:
            citations = [
                {"title": s.get("title", "Source"), "url": s.get("url", "")}
                for s in data["sources"]
            ]
        
        # Extract images
        images = data.get("images", [])
        
        return {
            "text": text,
            "citations": citations,
            "images": images,
            "model_used": model,
            "focus_mode": focus,
            "simulated": False
        }
    
    def ask_with_image(self,
                       query: str,
                       image_path: str,
                       model: str = "sonar-pro",
                       **kwargs) -> Dict[str, Any]:
        """
        Send a query with an image to Perplexity.
        
        Args:
            query: The question about the image
            image_path: Path to the image file
            model: Model to use (usually sonar-pro for vision)
            
        Returns:
            Dict with keys: 'text', 'model_used'
        """
        try:
            # Upload image first
            with open(image_path, 'rb') as f:
                files = {'file': f}
                upload_response = self.session.post(
                    "https://www.perplexity.ai/rest/ratelimit/upload",
                    files=files,
                    timeout=30
                )
                
                if upload_response.status_code != 200:
                    return {
                        "text": "❌ Falha ao fazer upload da imagem",
                        "model_used": model,
                        "error": "Upload failed"
                    }
                
                upload_data = upload_response.json()
                image_url = upload_data.get("url", "")
            
            # Now ask with the image URL
            payload = {
                "query": query,
                "model": model,
                "focus": "web",
                "image_url": image_url,
                "session_id": self._get_ws_sid(),
                "timestamp": int(time.time() * 1000)
            }
            
            response = self.session.post(
                "https://www.perplexity.ai/rest/ratelimit/search/ask",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "text": data.get("text", data.get("answer", "")),
                    "model_used": model,
                    "image_analyzed": True
                }
            else:
                return {
                    "text": "❌ Erro ao analisar imagem",
                    "model_used": model,
                    "error": f"HTTP {response.status_code}"
                }
                
        except FileNotFoundError:
            return {
                "text": "❌ Arquivo de imagem não encontrado",
                "model_used": model,
                "error": "File not found"
            }
        except Exception as e:
            return {
                "text": f"❌ Erro: {str(e)}",
                "model_used": model,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if the scraper is properly configured and available."""
        try:
            if not self.session_token:
                return False
            
            # Try to make a simple request
            response = self.session.get(
                "https://www.perplexity.ai/",
                timeout=10,
                allow_redirects=True
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def refresh_session(self) -> bool:
        """Refresh the session token."""
        try:
            self._ws_sid = None
            self._setup_headers()
            return self.is_available()
        except Exception:
            return False