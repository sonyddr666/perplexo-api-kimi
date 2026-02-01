"""
Base interface for Perplexity scrapers.
Defines the contract that all scraper implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class PerplexityModel(str, Enum):
    """Available Perplexity AI models (2026)."""
    SONAR = "sonar"                    # Llama 3.1 70B - Fast, 128K context
    SONAR_PRO = "sonar-pro"            # 2x retrieval, 200K context
    GPT_52 = "gpt-5.2"                 # OpenAI GPT-5.2
    REASONING_PRO = "reasoning-pro"    # Advanced logic
    DEEP_RESEARCH = "deep-research"    # Maximum research depth


class FocusMode(str, Enum):
    """Search focus modes."""
    WEB = "web"              # General web search
    ACADEMIC = "academic"    # Scientific papers
    WRITING = "writing"      # Creative writing
    VIDEO = "video"          # YouTube/Videos
    SOCIAL = "social"        # X/Reddit/Social
    MATH = "math"            # Mathematics
    WOLFRAM = "wolfram"      # Wolfram Alpha


class PerplexityScraperBase(ABC):
    """Abstract base class for Perplexity scrapers."""
    
    def __init__(self, session_token: Optional[str] = None, api_key: Optional[str] = None):
        self.session_token = session_token
        self.api_key = api_key
        self.base_url = "https://www.perplexity.ai"
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the scraper is properly configured and available."""
        pass
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        models_info = {
            PerplexityModel.SONAR: {
                "id": "sonar",
                "name": "Sonar",
                "speed": "10x faster",
                "context": "128K tokens",
                "description": "Fast, ideal for Q&A"
            },
            PerplexityModel.SONAR_PRO: {
                "id": "sonar-pro",
                "name": "Sonar Pro",
                "speed": "Moderate",
                "context": "200K tokens",
                "description": "2x retrieval depth, detailed analysis"
            },
            PerplexityModel.GPT_52: {
                "id": "gpt-5.2",
                "name": "GPT-5.2",
                "speed": "Moderate",
                "context": "128K tokens",
                "description": "OpenAI, coding and reasoning"
            },
            PerplexityModel.REASONING_PRO: {
                "id": "reasoning-pro",
                "name": "Reasoning Pro",
                "speed": "Moderate",
                "context": "128K tokens",
                "description": "Stepwise logic, complex problems"
            },
            PerplexityModel.DEEP_RESEARCH: {
                "id": "deep-research",
                "name": "Deep Research",
                "speed": "Lower",
                "context": "128K tokens",
                "description": "Maximum research, long reports"
            }
        }
        return models_info.get(model_id, models_info[PerplexityModel.SONAR])
    
    def get_focus_info(self, focus_id: str) -> Dict[str, Any]:
        """Get information about a focus mode."""
        focus_info = {
            FocusMode.WEB: {"id": "web", "description": "General web search"},
            FocusMode.ACADEMIC: {"id": "academic", "description": "Scientific papers"},
            FocusMode.WRITING: {"id": "writing", "description": "Creative content"},
            FocusMode.VIDEO: {"id": "video", "description": "YouTube and videos"},
            FocusMode.SOCIAL: {"id": "social", "description": "X, Reddit, forums"},
            FocusMode.MATH: {"id": "math", "description": "Mathematics"},
            FocusMode.WOLFRAM: {"id": "wolfram", "description": "Wolfram Alpha"}
        }
        return focus_info.get(focus_id, focus_info[FocusMode.WEB])
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models."""
        return [
            self.get_model_info(model) for model in PerplexityModel
        ]
    
    def list_focus_modes(self) -> List[Dict[str, Any]]:
        """List all available focus modes."""
        return [
            self.get_focus_info(focus) for focus in FocusMode
        ]