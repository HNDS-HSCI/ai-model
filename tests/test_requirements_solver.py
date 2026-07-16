"""
Tests for RequirementsSolver, LogicParser.parse_requirements,
and cognitive_core.py routing for REQUIREMENTS SPECIFICATION prompts.
"""

from __future__ import annotations

import time
import unittest
from typing import Dict

from hnsds.verifier.requirements_solver import (
    RequirementsSolver,
    SolverVerdict,
    ViolationKind,
)
from hnsds.perception.logic_parser import LogicParser


# ---------------------------------------------------------------------------
# RequirementsSolver unit tests
# ---------------------------------------------------------------------------

class TestRequirementsSolverSatisfiable(unittest.TestCase):
    """Green-path: consistent requirement sets."""

    def setUp(self) -> None:
        self.solver = RequirementsSolver()

    def test_empty_solver_is_satisfiable(self) -> None:
        result = self.solver.solve()
        self.assertEqual(result.verdict, SolverVerdict.SATISFIABLE)
        self.assertTrue(result.is_valid())

    def test_single_required_feature(self) -> None:
        self.solver.require("auth")
        result = self.solver.solve()
        self.assertEqual(result.verdict, SolverVerdict.SATISFIABLE)
        self.assertIn("auth", result.model)
        self.assertTrue(result.model["auth"])

    def test_required_with_satisfied_prerequisite(self) -> None:
        self.solver.require("payments")
        self.solver.require("auth")
        self.solver.add_prerequisite("payments", "auth")
        result = self.solver.solve()
        self.assertEqual(result.verdict, SolverVerdict.SATISFIABLE)

    def test_dependency_chain_satisfiable(self) -> None:
        self.solver.require("feature-c")
        self.solver.require("feature-b")
        self.solver.require("feature-a")
        self.solver.add_dependency("feature-c", "feature-b")
        self.solver.add_dependency("feature-b", "feature-a")
        result = self.solver.solve()
        self.assertTrue(result.is_valid())

    def test_non_mutex_features_coexist(self) -> None:
        self.solver.require("dark-mode")
        self.solver.require("notifications")
        self.solver.add_mutual_exclusion("dark-mode", "high-contrast")
        result = self.solver.solve()
        self.assertTrue(result.is_valid())


class TestRequirementsSolverConflicts(unittest.TestCase):
    """Conflict detection."""

    def setUp(self) -> None:
        self.solver = RequirementsSolver()

    def test_conflict_same_feature_required_and_disabled(self) -> None:
        self.solver.require("logging")
        self.solver.disable("logging")
        result = self.solver.solve()
        self.assertEqual(result.verdict, SolverVerdict.UNSATISFIABLE)
        kinds = {v.kind for v in result.violations}
        self.assertIn(ViolationKind.CONFLICT, kinds)

    def test_conflict_detail_mentions_feature(self) -> None:
        self.solver.require("offline-mode")
        self.solver.disable("offline-mode")
        result = self.solver.solve()
        detail = result.violations[0].detail
        self.assertIn("offline-mode", detail)

    def test_z3_detects_unsat_with_implies_false(self) -> None:
        # A required, B required, B implies NOT A → unsat
        self.solver.require("A")
        self.solver.require("B")
        # B → ¬A expressed as mutex(A,B) + require both
        self.solver.add_mutual_exclusion("A", "B")
        result = self.solver.solve()
        self.assertNotEqual(result.verdict, SolverVerdict.SATISFIABLE)


class TestRequirementsSolverMissingPrereq(unittest.TestCase):
    """Missing prerequisite detection."""

    def setUp(self) -> None:
        self.solver = RequirementsSolver()

    def test_prereq_disabled_raises_violation(self) -> None:
        self.solver.require("checkout")
        self.solver.disable("payment-gateway")
        self.solver.add_prerequisite("checkout", "payment-gateway")
        result = self.solver.solve()
        kinds = {v.kind for v in result.violations}
        self.assertIn(ViolationKind.MISSING_PREREQ, kinds)

    def test_prereq_not_required_but_implied(self) -> None:
        # checkout requires payment-gateway; payment-gateway not required/disabled
        # Z3 should find a model where payment-gateway=True
        self.solver.require("checkout")
        self.solver.add_prerequisite("checkout", "payment-gateway")
        result = self.solver.solve()
        self.assertEqual(result.verdict, SolverVerdict.SATISFIABLE)
        self.assertTrue(result.model.get("payment-gateway", False))

    def test_validate_catches_missing_prereq_in_assignment(self) -> None:
        self.solver.require("checkout")
        self.solver.add_prerequisite("checkout", "payment-gateway")
        # Assignment activates checkout but NOT payment-gateway
        assignment: Dict[str, bool] = {"checkout": True, "payment-gateway": False}
        result = self.solver.validate(assignment)
        self.assertEqual(result.verdict, SolverVerdict.UNSATISFIABLE)
        kinds = {v.kind for v in result.violations}
        self.assertIn(ViolationKind.MISSING_PREREQ, kinds)


class TestRequirementsSolverMutualExclusion(unittest.TestCase):
    """Mutual exclusion detection."""

    def setUp(self) -> None:
        self.solver = RequirementsSolver()

    def test_both_mutex_features_required(self) -> None:
        self.solver.require("free-plan")
        self.solver.require("paid-plan")
        self.solver.add_mutual_exclusion("free-plan", "paid-plan")
        result = self.solver.solve()
        kinds = {v.kind for v in result.violations}
        self.assertIn(ViolationKind.MUTUAL_EXCLUSION, kinds)

    def test_mutex_one_required_other_not(self) -> None:
        self.solver.require("free-plan")
        self.solver.add_mutual_exclusion("free-plan", "paid-plan")
        result = self.solver.solve()
        self.assertTrue(result.is_valid())

    def test_validate_mutex_both_active(self) -> None:
        self.solver.add_mutual_exclusion("X", "Y")
        result = self.solver.validate({"X": True, "Y": True})
        kinds = {v.kind for v in result.violations}
        self.assertIn(ViolationKind.MUTUAL_EXCLUSION, kinds)

    def test_validate_mutex_one_active(self) -> None:
        self.solver.add_mutual_exclusion("X", "Y")
        result = self.solver.validate({"X": True, "Y": False})
        self.assertEqual(result.verdict, SolverVerdict.SATISFIABLE)


class TestRequirementsSolverDependencyViolation(unittest.TestCase):
    """Dependency violation detection."""

    def setUp(self) -> None:
        self.solver = RequirementsSolver()

    def test_dependent_required_dependency_disabled(self) -> None:
        self.solver.require("api-v2")
        self.solver.disable("api-v1")
        self.solver.add_dependency("api-v2", "api-v1")
        result = self.solver.solve()
        kinds = {v.kind for v in result.violations}
        self.assertIn(ViolationKind.DEPENDENCY_FAULT, kinds)

    def test_dependency_chain_violation(self) -> None:
        self.solver.require("C")
        self.solver.disable("A")
        self.solver.add_dependency("C", "B")
        self.solver.add_dependency("B", "A")
        result = self.solver.solve()
        # Z3 or structural check must report unsat/violation
        self.assertNotEqual(result.verdict, SolverVerdict.SATISFIABLE)

    def test_validate_dependency_fault_in_assignment(self) -> None:
        self.solver.add_dependency("reports", "database")
        assignment: Dict[str, bool] = {"reports": True, "database": False}
        result = self.solver.validate(assignment)
        kinds = {v.kind for v in result.violations}
        self.assertIn(ViolationKind.DEPENDENCY_FAULT, kinds)


class TestRequirementsSolverEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions."""

    def test_feature_declared_multiple_times_is_idempotent(self) -> None:
        solver = RequirementsSolver()
        solver.add_feature("alpha")
        solver.add_feature("alpha")
        solver.require("alpha")
        result = solver.solve()
        self.assertEqual(result.verdict, SolverVerdict.SATISFIABLE)

    def test_empty_assignment_validate(self) -> None:
        solver = RequirementsSolver()
        solver.require("X")
        result = solver.validate({})
        self.assertEqual(result.verdict, SolverVerdict.UNSATISFIABLE)

    def test_explain_returns_all_constraints(self) -> None:
        solver = RequirementsSolver()
        solver.require("A")
        solver.disable("B")
        solver.add_prerequisite("A", "C")
        solver.add_mutual_exclusion("D", "E")
        solver.add_dependency("F", "G")
        lines = solver.explain()
        self.assertTrue(any("REQUIRE" in l for l in lines))
        self.assertTrue(any("DISABLE" in l for l in lines))
        self.assertTrue(any("PREREQ" in l for l in lines))
        self.assertTrue(any("MUTEX" in l for l in lines))
        self.assertTrue(any("DEPENDS" in l for l in lines))

    def test_result_str_valid(self) -> None:
        solver = RequirementsSolver()
        solver.require("X")
        result = solver.solve()
        self.assertEqual(str(result), "VALID")

    def test_result_str_invalid_contains_verdict(self) -> None:
        solver = RequirementsSolver()
        solver.require("X")
        solver.disable("X")
        result = solver.solve()
        self.assertIn("UNSATISFIABLE", str(result))

    def test_violation_str(self) -> None:
        solver = RequirementsSolver()
        solver.require("F")
        solver.disable("F")
        result = solver.solve()
        v_str = str(result.violations[0])
        self.assertIn("CONFLICT", v_str)


class TestRequirementsSolverPerformance(unittest.TestCase):
    """Performance: <20 ms for 50-feature problem."""

    def test_large_problem_under_20ms(self) -> None:
        solver = RequirementsSolver()
        features = [f"feat_{i}" for i in range(50)]
        for f in features:
            solver.add_feature(f)
        for i in range(0, 48, 2):
            solver.add_dependency(features[i], features[i + 1])
        solver.require(features[0])

        start = time.perf_counter()
        result = solver.solve()
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.assertLess(elapsed_ms, 20, f"Solver took {elapsed_ms:.1f}ms (limit 20ms)")
        self.assertEqual(result.verdict, SolverVerdict.SATISFIABLE)


# ---------------------------------------------------------------------------
# LogicParser.parse_requirements unit tests
# ---------------------------------------------------------------------------

class TestLogicParserParseRequirements(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = LogicParser()

    def test_parses_required_features(self) -> None:
        text = "Feature auth is required.\nFeature logging is enabled."
        parsed = self.parser.parse_requirements(text)
        self.assertIn("auth", parsed["required"])
        self.assertIn("logging", parsed["required"])

    def test_parses_disabled_features(self) -> None:
        text = "Feature legacy-api is disabled.\nFeature debug is not available."
        parsed = self.parser.parse_requirements(text)
        self.assertIn("legacy-api", parsed["disabled"])
        self.assertIn("debug", parsed["disabled"])

    def test_parses_enable_disable_shorthand(self) -> None:
        text = "ENABLE: payments\nDISABLE: mock-data"
        parsed = self.parser.parse_requirements(text)
        self.assertIn("payments", parsed["required"])
        self.assertIn("mock-data", parsed["disabled"])

    def test_parses_mutual_exclusion(self) -> None:
        text = "free-plan and paid-plan are mutually exclusive."
        parsed = self.parser.parse_requirements(text)
        self.assertEqual(len(parsed["mutual_exclusions"]), 1)
        self.assertEqual(parsed["mutual_exclusions"][0]["a"], "free-plan")
        self.assertEqual(parsed["mutual_exclusions"][0]["b"], "paid-plan")

    def test_parses_dependencies(self) -> None:
        text = "checkout requires payment-gateway."
        parsed = self.parser.parse_requirements(text)
        self.assertEqual(len(parsed["dependencies"]), 1)
        dep = parsed["dependencies"][0]
        self.assertEqual(dep["dependent"], "checkout")
        self.assertEqual(dep["dependency"], "payment-gateway")

    def test_parses_explicit_conflict(self) -> None:
        text = "CONFLICT: feature-A and feature-B"
        parsed = self.parser.parse_requirements(text)
        self.assertEqual(len(parsed["explicit_conflicts"]), 1)
        self.assertEqual(parsed["explicit_conflicts"][0]["a"], "feature-A")
        self.assertEqual(parsed["explicit_conflicts"][0]["b"], "feature-B")

    def test_empty_text_returns_empty_structure(self) -> None:
        parsed = self.parser.parse_requirements("")
        for key, val in parsed.items():
            self.assertEqual(val, [], f"Expected empty list for '{key}'")

    def test_no_duplicates_in_required(self) -> None:
        text = "Feature auth is required.\nFeature auth is required."
        parsed = self.parser.parse_requirements(text)
        self.assertEqual(parsed["required"].count("auth"), 1)

    def test_complex_requirements_block(self) -> None:
        text = """
REQUIREMENTS SPECIFICATION:
Feature auth is required.
Feature payments is required.
Feature legacy-api is disabled.
payments requires auth.
free-tier and enterprise are mutually exclusive.
Feature free-tier is required.
CONFLICT: feature-x and feature-y
"""
        parsed = self.parser.parse_requirements(text)
        self.assertIn("auth", parsed["required"])
        self.assertIn("payments", parsed["required"])
        self.assertIn("legacy-api", parsed["disabled"])
        self.assertEqual(len(parsed["dependencies"]), 1)
        self.assertEqual(len(parsed["mutual_exclusions"]), 1)
        self.assertEqual(len(parsed["explicit_conflicts"]), 1)


# ---------------------------------------------------------------------------
# cognitive_core integration tests
# ---------------------------------------------------------------------------

class TestCognitiveCoreRequirementsRouting(unittest.TestCase):

    def setUp(self) -> None:
        from hnsds.brain.cognitive_core import HyperSymbolicBrain
        self.brain = HyperSymbolicBrain()

    def test_satisfiable_spec_returns_satisfiable(self) -> None:
        prompt = """REQUIREMENTS SPECIFICATION:
Feature auth is required.
Feature payments is required.
payments requires auth.
"""
        response = self.brain.process(prompt)
        self.assertIn("SATISFIABLE", response)

    def test_conflicting_spec_returns_violation_kind(self) -> None:
        prompt = """REQUIREMENTS SPECIFICATION:
Feature offline-mode is required.
Feature offline-mode is disabled.
"""
        response = self.brain.process(prompt)
        # Must contain CONFLICT or UNSATISFIABLE
        self.assertTrue(
            "CONFLICT" in response or "UNSATISFIABLE" in response,
            msg=f"Unexpected response: {response}",
        )

    def test_mutex_violation_detected(self) -> None:
        prompt = """REQUIREMENTS SPECIFICATION:
Feature free-plan is required.
Feature paid-plan is required.
free-plan and paid-plan are mutually exclusive.
"""
        response = self.brain.process(prompt)
        self.assertTrue(
            "MUTUAL_EXCLUSION" in response or "UNSATISFIABLE" in response,
            msg=f"Unexpected response: {response}",
        )

    def test_dependency_fault_detected(self) -> None:
        prompt = """REQUIREMENTS SPECIFICATION:
Feature api-v2 is required.
Feature api-v1 is disabled.
DEPENDENCY_FAULT: api-v2 -> api-v1
"""
        response = self.brain.process(prompt)
        self.assertTrue(
            "DEPENDENCY_FAULT" in response or "UNSATISFIABLE" in response,
            msg=f"Unexpected response: {response}",
        )


if __name__ == "__main__":
    unittest.main()
