"""
Embeddings module using Gemini API.
Generates vector embeddings for code chunks.
"""

import httpx
from typing import List
from app.core.key_manager import key_manager


class EmbeddingsClient:
    """Generates embeddings using Gemini's embedding API."""
    
    def __init__(self):
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
    
    async def embed(self, text: str) -> List[float]:
        """Generates an embedding for a single text."""
        
        api_key = key_manager.get_next_key()
        if not api_key:
            raise ValueError("No API keys available")
        
        url = f"{self.base_url}?key={api_key}"
        payload = {
            "content": {
                "parts": [{"text": text}]
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding", {}).get("values", [])
            
            elif response.status_code == 429:
                key_manager.report_rate_limit(api_key)
                # Retry with next key
                return await self.embed(text)
            
            else:
                print(f"Embedding API Error {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            print(f"Embedding request failed: {e}")
            return []
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            emb = await self.embed(text)
            embeddings.append(emb)
        return embeddings


embeddings_client = EmbeddingsClient()
