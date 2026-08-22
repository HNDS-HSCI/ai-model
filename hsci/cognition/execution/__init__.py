"""HSCI Cognition Execution Subsystem (Sprint VS-5).

Orchestrates the deterministic execution of CognitiveTasks over the HSCI cognitive stack
(KnowledgeManager, ConceptActivationEngine, CognitiveReasoningEngine, AnswerGenerationEngine,
and ExplanatoryAnswerSynthesizer).
"""
from hsci.cognition.execution.execution_result import CognitiveExecutionResult
from hsci.cognition.execution.task_executor import CognitiveTaskExecutor

__all__ = [
    "CognitiveExecutionResult",
    "CognitiveTaskExecutor",
]
