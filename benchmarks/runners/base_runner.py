import abc

class BaseRunner(abc.ABC):
    def __init__(self, name):
        self.name = name

    @abc.abstractmethod
    def run(self, prompt: str) -> str:
        """Executes the prompt and returns the output."""
        pass
