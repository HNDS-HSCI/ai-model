import os
import requests
from .base_runner import BaseRunner

class ClaudeRunner(BaseRunner):
    def __init__(self, model="claude-3-opus-20240229"):
        super().__init__("Claude-3")
        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    def run(self, prompt: str) -> str:
        if not self.api_key:
            return "MOCK_RESPONSE: Anthropic API Key missing."
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        data = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception as e:
            return f"ERROR: {str(e)}"
