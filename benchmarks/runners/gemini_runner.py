import os
import requests
from .base_runner import BaseRunner

class GeminiRunner(BaseRunner):
    def __init__(self, model="gemini-1.5-pro"):
        super().__init__("Gemini")
        self.model = model
        self.api_key = os.environ.get("GEMINI_API_KEY", "")

    def run(self, prompt: str) -> str:
        if not self.api_key:
            return "MOCK_RESPONSE: Gemini API Key missing."
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return f"ERROR: {str(e)}"
