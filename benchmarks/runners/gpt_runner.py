import os
import requests
from .base_runner import BaseRunner

class GPTRunner(BaseRunner):
    def __init__(self, model="gpt-4"):
        super().__init__("GPT-4")
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY", "")

    def run(self, prompt: str) -> str:
        if not self.api_key:
            return "MOCK_RESPONSE: OpenAI API Key missing."
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"ERROR: {str(e)}"
