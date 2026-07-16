"""
RequirementsSolver — Z3-backed requirements consistency checker.

Detects:
  - Conflicting requirements  (A required AND NOT A required)
  - Missing prerequisites     (A required but its prereq is absent)
  - Mutually exclusive pairs  (A and B cannot both be active)
  - Dependency violations     (A depends on B but B is disabled/absent)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import z3


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class ViolationKind(Enum):
    CONFLICT           = auto()
    MISSING_PREREQ     = auto()
    MUTUAL_EXCLUSION   = auto()
    DEPENDENCY_FAULT   = auto()


@dataclass(frozen=True)
class Violation:
    kind:    ViolationKind
    items:   Tuple[str, ...]
    detail:  str

    def __str__(self) -> str:
        return f"[{self.kind.name}] {self.detail}"


class SolverVerdict(Enum):
    SATISFIABLE   = "SATISFIABLE"
    UNSATISFIABLE = "UNSATISFIABLE"
    UNKNOWN       = "UNKNOWN"


@dataclass
class RequirementsResult:
    verdict:    SolverVerdict
    violations: List[Violation] = field(default_factory=list)
    model:      Optional[Dict[str, bool]] = None

    def is_valid(self) -> bool:
        return self.verdict == SolverVerdict.SATISFIABLE and not self.violations

    def __str__(self) -> str:
        if self.is_valid():
            return "VALID"
        lines = [self.verdict.value]
        for v in self.violations:
            lines.append(f"  {v}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class RequirementsSolver:
    """
    Deterministic requirements-consistency solver backed by Z3 Bool logic.

    Interface
    ---------
    add_feature(name)                         — declare a feature variable
    require(name)                             — feature must be True
    disable(name)                             — feature must be False
    add_prerequisite(feature, prereq)         — Implies(feature, prereq)
    add_mutual_exclusion(a, b)                — Not(And(a, b))
    add_dependency(dependent, dependency)     — Implies(dependent, dependency)
    solve() -> RequirementsResult
    validate(assignment) -> RequirementsResult
    explain() -> List[str]
    """

    def __init__(self) -> None:
        self._vars:            Dict[str, z3.BoolRef] = {}
        self._required:        Set[str]              = set()
        self._disabled:        Set[str]              = set()
        self._prerequisites:   List[Tuple[str, str]] = []   # (feature, prereq)
        self._mutual_excl:     List[Tuple[str, str]] = []   # (a, b)
        self._dependencies:    List[Tuple[str, str]] = []   # (dependent, dep)

    # ------------------------------------------------------------------
    # Declaration API
    # ------------------------------------------------------------------

    def add_feature(self, name: str) -> None:
        """Declare a Bool variable for a feature (idempotent)."""
        if name not in self._vars:
            self._vars[name] = z3.Bool(name)

    def require(self, name: str) -> None:
        """Assert that *name* must be active."""
        self.add_feature(name)
        self._required.add(name)

    def disable(self, name: str) -> None:
        """Assert that *name* must be inactive."""
        self.add_feature(name)
        self._disabled.add(name)

    def add_prerequisite(self, feature: str, prereq: str) -> None:
        """If *feature* is active then *prereq* must also be active."""
        self.add_feature(feature)
        self.add_feature(prereq)
        self._prerequisites.append((feature, prereq))

    def add_mutual_exclusion(self, a: str, b: str) -> None:
        """*a* and *b* cannot both be active simultaneously."""
        self.add_feature(a)
        self.add_feature(b)
        self._mutual_excl.append((a, b))

    def add_dependency(self, dependent: str, dependency: str) -> None:
        """If *dependent* is active then *dependency* must also be active."""
        self.add_feature(dependent)
        self.add_feature(dependency)
        self._dependencies.append((dependent, dependency))

    # ------------------------------------------------------------------
    # Core solve
    # ------------------------------------------------------------------

    def solve(self) -> RequirementsResult:
        """
        Analyse the full constraint set and return a RequirementsResult.

        Violations are detected in two passes:
          1. Structural pre-check (no Z3 needed): conflicts, missing prereqs,
             mutual-exclusion clashes, dependency faults.
          2. Z3 SAT check: if structural pass is clean, verify satisfiability.
        """
        violations = self._structural_check()

        solver = self._build_solver()
        z3_result = solver.check()

        if z3_result == z3.sat:
            verdict = SolverVerdict.SATISFIABLE
            model = self._extract_model(solver.model())
        elif z3_result == z3.unsat:
            verdict = SolverVerdict.UNSATISFIABLE
            model = None
            if not violations:
                # Z3 found unsat but structural pass was clean — collect Z3 violation
                violations.append(Violation(
                    kind=ViolationKind.CONFLICT,
                    items=tuple(self._required | self._disabled),
                    detail="Z3 determined constraint set is unsatisfiable.",
                ))
        else:
            verdict = SolverVerdict.UNKNOWN
            model = None

        return RequirementsResult(verdict=verdict, violations=violations, model=model)

    def validate(self, assignment: Dict[str, bool]) -> RequirementsResult:
        """
        Check whether a concrete *assignment* satisfies all registered constraints.
        Returns RequirementsResult (verdict=SATISFIABLE if OK).
        """
        violations: List[Violation] = []

        for feat, var in self._vars.items():
            val = assignment.get(feat, False)

            if feat in self._required and not val:
                violations.append(Violation(
                    kind=ViolationKind.MISSING_PREREQ,
                    items=(feat,),
                    detail=f"Required feature '{feat}' is not active in assignment.",
                ))
            if feat in self._disabled and val:
                violations.append(Violation(
                    kind=ViolationKind.CONFLICT,
                    items=(feat,),
                    detail=f"Disabled feature '{feat}' is active in assignment.",
                ))

        for (feature, prereq) in self._prerequisites:
            if assignment.get(feature, False) and not assignment.get(prereq, False):
                violations.append(Violation(
                    kind=ViolationKind.MISSING_PREREQ,
                    items=(feature, prereq),
                    detail=f"Feature '{feature}' is active but prerequisite '{prereq}' is missing.",
                ))

        for (a, b) in self._mutual_excl:
            if assignment.get(a, False) and assignment.get(b, False):
                violations.append(Violation(
                    kind=ViolationKind.MUTUAL_EXCLUSION,
                    items=(a, b),
                    detail=f"Mutually exclusive features '{a}' and '{b}' are both active.",
                ))

        for (dependent, dep) in self._dependencies:
            if assignment.get(dependent, False) and not assignment.get(dep, False):
                violations.append(Violation(
                    kind=ViolationKind.DEPENDENCY_FAULT,
                    items=(dependent, dep),
                    detail=f"'{dependent}' depends on '{dep}' but '{dep}' is not active.",
                ))

        verdict = SolverVerdict.SATISFIABLE if not violations else SolverVerdict.UNSATISFIABLE
        return RequirementsResult(verdict=verdict, violations=violations, model=assignment)

    def explain(self) -> List[str]:
        """Return human-readable description of every registered constraint."""
        lines: List[str] = []
        for f in sorted(self._required):
            lines.append(f"REQUIRE: {f}")
        for f in sorted(self._disabled):
            lines.append(f"DISABLE: {f}")
        for (f, p) in self._prerequisites:
            lines.append(f"PREREQ: {f} => {p}")
        for (a, b) in self._mutual_excl:
            lines.append(f"MUTEX: {a} XOR {b}")
        for (d, dep) in self._dependencies:
            lines.append(f"DEPENDS: {d} => {dep}")
        return lines

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _structural_check(self) -> List[Violation]:
        """Fast pre-pass — no Z3 needed."""
        violations: List[Violation] = []

        # 1. Conflict: same feature required AND disabled
        conflicts: Set[str] = self._required & self._disabled
        for f in sorted(conflicts):
            violations.append(Violation(
                kind=ViolationKind.CONFLICT,
                items=(f,),
                detail=f"Feature '{f}' is both required and disabled.",
            ))

        # 2. Missing prerequisites: required feature whose prereq is disabled/absent
        for (feature, prereq) in self._prerequisites:
            if feature in self._required:
                if prereq in self._disabled:
                    violations.append(Violation(
                        kind=ViolationKind.MISSING_PREREQ,
                        items=(feature, prereq),
                        detail=(
                            f"Feature '{feature}' is required but its prerequisite "
                            f"'{prereq}' is disabled."
                        ),
                    ))

        # 3. Mutual exclusion: both members required
        for (a, b) in self._mutual_excl:
            if a in self._required and b in self._required:
                violations.append(Violation(
                    kind=ViolationKind.MUTUAL_EXCLUSION,
                    items=(a, b),
                    detail=f"Mutually exclusive features '{a}' and '{b}' are both required.",
                ))

        # 4. Dependency violations: dependent is required but dependency is disabled
        for (dependent, dep) in self._dependencies:
            if dependent in self._required and dep in self._disabled:
                violations.append(Violation(
                    kind=ViolationKind.DEPENDENCY_FAULT,
                    items=(dependent, dep),
                    detail=(
                        f"'{dependent}' is required and depends on '{dep}', "
                        f"but '{dep}' is disabled."
                    ),
                ))

        return violations

    def _build_solver(self) -> z3.Solver:
        solver = z3.Solver()

        for f in self._required:
            solver.add(self._vars[f])

        for f in self._disabled:
            solver.add(z3.Not(self._vars[f]))

        for (feature, prereq) in self._prerequisites:
            solver.add(z3.Implies(self._vars[feature], self._vars[prereq]))

        for (a, b) in self._mutual_excl:
            solver.add(z3.Not(z3.And(self._vars[a], self._vars[b])))

        for (dependent, dep) in self._dependencies:
            solver.add(z3.Implies(self._vars[dependent], self._vars[dep]))

        return solver

    @staticmethod
    def _extract_model(z3_model: z3.ModelRef) -> Dict[str, bool]:
        result: Dict[str, bool] = {}
        for decl in z3_model.decls():
            val = z3_model[decl]
            result[decl.name()] = bool(z3.is_true(val))
        return result
