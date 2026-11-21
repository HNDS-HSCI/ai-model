"""HSCI Mind: a knowledge-driven neuro-symbolic reasoning core.

Knowledge comes in as English, is compiled into logic, and every answer is derived
by proof and re-checked by Z3. See ``docs/mind/ARCHITECTURE.md``.

    from hsci.mind import Mind
    mind = Mind()
    mind.process("Socrates is a man. All men are mortal. Is Socrates mortal?").reply
"""
from hsci.mind.mind import Item, Mind, MindResponse

__all__ = ["Mind", "MindResponse", "Item"]
