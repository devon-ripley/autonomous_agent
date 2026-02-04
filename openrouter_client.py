"""
OpenRouter API client for LLM communication.
Handles requests to OpenRouter API with retry logic and error handling.
"""
import time
from typing import List, Dict, Iterator, Optional
from openai import OpenAI
from config import Config


class OpenRouterClient:
    """Client for interacting with OpenRouter API."""
    
    def __init__(self):
        """Initialize the OpenRouter client."""
        self.client = OpenAI(
            base_url=Config.OPENROUTER_BASE_URL,
            api_key=Config.OPENROUTER_API_KEY,
        )
        self.model = Config.OPENROUTER_MODEL
        self.temperature = Config.TEMPERATURE
        self.max_tokens = Config.MAX_TOKENS
        self.request_count = 0
        self.total_tokens = 0
        self._last_request_time = 0
    
    def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        if Config.RATE_LIMIT_SECONDS > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < Config.RATE_LIMIT_SECONDS:
                time.sleep(Config.RATE_LIMIT_SECONDS - elapsed)
        self._last_request_time = time.time()
    
    def send_message(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict:
        """
        Send a message to the LLM and get a complete response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Returns:
            Dict with 'content', 'model', 'usage' keys
        """
        self._apply_rate_limit()
        
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tok,
                )
                
                self.request_count += 1
                if hasattr(response, 'usage') and response.usage:
                    self.total_tokens += response.usage.total_tokens
                
                return {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "usage": response.usage.model_dump() if hasattr(response, 'usage') and response.usage else None,
                    "finish_reason": response.choices[0].finish_reason,
                }
                
            except Exception as e:
                if attempt < Config.MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    print(f"API request failed (attempt {attempt + 1}/{Config.MAX_RETRIES}): {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"API request failed after {Config.MAX_RETRIES} attempts: {e}")
    
    def stream_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> Iterator[str]:
        """
        Stream a response from the LLM token by token.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            
        Yields:
            String chunks as they arrive
        """
        self._apply_rate_limit()
        temp = temperature if temperature is not None else self.temperature
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=self.max_tokens,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
            self.request_count += 1
            
        except Exception as e:
            raise Exception(f"Streaming request failed: {e}")
    
    def get_statistics(self) -> Dict:
        """Get usage statistics for this client instance."""
        return {
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "model": self.model,
        }
