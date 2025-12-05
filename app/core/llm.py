import httpx
from app.core.key_manager import key_manager

class GeminiClient:
    def __init__(self):
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    async def generate_content(self, prompt: str) -> str:
        """Generates content using Gemini REST API with key rotation."""
        
        # Try up to 3 times to get a working key
        for _ in range(3):
            api_key = key_manager.get_next_key()
            if not api_key:
                print("Error: No API keys available.")
                return "Error: Service unavailable (No API keys)."
            
            url = f"{self.base_url}?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=payload, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    try:
                        return data['candidates'][0]['content']['parts'][0]['text']
                    except (KeyError, IndexError):
                        print(f"Unexpected response format: {data}")
                        return ""
                
                elif response.status_code == 429:
                    print(f"Rate limit hit for key ...{api_key[-4:]}")
                    key_manager.report_rate_limit(api_key)
                    continue  # Try next key
                
                else:
                    print(f"Gemini API Error {response.status_code}: {response.text}")
                    return f"Error: Gemini API returned {response.status_code}"
                    
            except Exception as e:
                print(f"Request failed: {e}")
                return f"Error: Request failed - {e}"
        
        return "Error: All attempts failed."

llm_client = GeminiClient()
