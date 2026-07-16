import sys
import os
# Add the root directory to path so we can import hnsds
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from hnsds.brain.cognitive_core import HyperSymbolicBrain
from .base_runner import BaseRunner

class HSCIRunner(BaseRunner):
    def __init__(self):
        super().__init__("HSCI")
        self.brain = HyperSymbolicBrain()

    def run(self, prompt: str) -> str:
        try:
            return self.brain.process(prompt)
        except Exception as e:
            return f"ERROR: {str(e)}"
