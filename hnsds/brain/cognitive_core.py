import logging
import json
from hnsds.perception.logic_parser import LogicParser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.enumerative import EnumerativeSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger
from hnsds.mental_model import MentalModel
from hnsds.brain.lobes.native_engine import NativeSymbolicEngine
from hnsds.brain.lobes.cognitive_lobe import CognitiveAwareness
from hnsds.verifier.graph_solver import GraphSolver
from hnsds.verifier.dependency_solver import DependencySolver
from hnsds.verifier.requirements_solver import RequirementsSolver

logging.basicConfig(level=logging.DEBUG)


class HyperSymbolicBrain:
    """
    INVENTION: The Autonomous Hyper-Symbolic Brain.
    
    NEW ARCHITECTURE: System Awareness & Axiomatic Logic.
    Processes information by comprehending the whole context as an environment
    and applying mastered mental axioms to solve gaps.
    """

    def __init__(self):
        self.logger = logging.getLogger("CognitiveCore")

        # Native Lobe Initialization
        self.awareness_lobe = CognitiveAwareness()
        self.logic_prover = Z3Verifier()      
        self.csp_engine = NativeSymbolicEngine() 
        self.memory_lobe = EpisodeLogger()
        self.logic_parser = LogicParser()
        self.synthesizer = EnumerativeSynthesizer(learner=self.memory_lobe)
        self.planner = HTNPlanner()
        self.graph_engine = GraphSolver()
        self.dependency_engine = DependencySolver()
        self.requirements_engine = RequirementsSolver()

        # The Active Mind
        self.mind = MentalModel(learner=self.memory_lobe, cognitive_lobe=self.awareness_lobe)
        
    def teach(self, stimulus, concept_name, axiom):
        """
        Interactive Teaching API: Allows humans to teach the system new concepts.
        """
        self.logger.info(f"TEACHING: Binding stimulus to concept '{concept_name}' using axiom '{axiom}'")
        self.awareness_lobe.teach_concept(concept_name, stimulus, axiom)
        return f"Learned concept: {concept_name} -> Maps to {axiom}"

    def process(self, stimulus, budget=5):
        self.mind.memory_trace = []
        self.mind.state = "IDLE"

        # 0.0 Check for Interactive Teaching
        if stimulus.lower().startswith("teach:"):
            parts = stimulus[6:].split("|")
            if len(parts) >= 3:
                return self.teach(parts[0].strip(), parts[1].strip(), parts[2].strip().upper())
            return "Teach format: 'teach: <stimulus> | <concept_name> | <axiom>'"

        self.logger.info(f"Local Brain Activity: Comprehending environment '{stimulus[:50]}...'")

        # 1. PERCEPTION: Map the Environment and State Gap
        env = self.awareness_lobe.perceive_environment(stimulus)
        self.mind.memory_trace.append(f"AWARENESS: Environmental Map established ({len(env['entities'])} entities)")

        # 2. DELIBERATION: Generate the Universal Sigma (Σ) Contract
        deliberation = self.awareness_lobe.deliberate(env)
        master_sigma = deliberation["goal"]
        rationale = deliberation.get("rationale", "No rationale generated.")
        
        self.mind.memory_trace.append(f"DELIBERATION: State Gap identified. Rationale: {rationale}")
        
        is_graph_task = "ENTERPRISE DEPLOYMENT TOPOLOGY" in stimulus or "PACKAGE MANAGER RESOLUTION GRAPH" in stimulus or "ENTERPRISE WORKFLOW STATE MACHINE" in stimulus or "GLOBAL RESOURCE ALLOCATION MATRIX" in stimulus or "REQUIREMENTS SPECIFICATION" in stimulus
        if deliberation["axiom"] == "TRANSFORMATION" and not is_graph_task:
            return f"[TRANSFORMATION] {master_sigma.get('response', 'Environment processed.')}"

        # 3. RECURSIVE PLANNING: Decompose Goal into Logical Steps
        subgoals = self.planner.decompose(master_sigma)
        final_results = []

        # 4. UNIFIED REASONING MESH: Solve the constraints
        for i, sigma in enumerate(subgoals):
            step_name = sigma.get("step", f"Task {i+1}")
            self.logger.info(f"REASONING_ON_SUBGOAL: {step_name}")
            
            # The brain now cycles through its lobes to find the best fit for the constraint
            # It doesn't care if it's 'math' or 'code', it only cares if it's PROVEN.
            solution_found = False
            candidate = None
            
            # Priority 0.5: Deterministic Graph/DAG Verification
            if not solution_found and ("ENTERPRISE DEPLOYMENT TOPOLOGY" in stimulus or "PACKAGE MANAGER RESOLUTION GRAPH" in stimulus):
                parsed_graph = self.logic_parser.parse_graph(stimulus)
                
                if "PACKAGE MANAGER RESOLUTION GRAPH" in stimulus:
                    self.dependency_engine = DependencySolver()
                    for pkg in parsed_graph["packages"]:
                        self.dependency_engine.register_package(pkg["id"], pkg["version"])
                    for edge in parsed_graph["edges"]:
                        self.dependency_engine.add_dependency(edge["source"], edge["target"], edge.get("expected_version"))
                    
                    candidate = self.dependency_engine.resolve()
                    solution_found = True
                    method = "DETERMINISTIC_GRAPH_TRAVERSAL"
                    
                elif "ENTERPRISE DEPLOYMENT TOPOLOGY" in stimulus:
                    self.graph_engine = GraphSolver()
                    for node in parsed_graph["nodes"]:
                        self.graph_engine.add_node(node["id"], node["properties"])
                    for edge in parsed_graph["edges"]:
                        self.graph_engine.add_edge(edge["source"], edge["target"])
                        
                    is_valid = True
                    if parsed_graph["regional_rules"]:
                        rules = [(r["src_region"], r["tgt_region"]) for r in parsed_graph["regional_rules"]]
                        if not self.graph_engine.verify_regional_compliance(rules):
                            candidate = "INVALID_ORDER"
                            is_valid = False
                            
                    if is_valid:
                        cycle = self.graph_engine.detect_cycles()
                        if cycle:
                            candidate = "CYCLIC_DEPENDENCY"
                        else:
                            candidate = "VALID_ORDER"
                            
                    solution_found = True
                    method = "DETERMINISTIC_GRAPH_TRAVERSAL"

            # Priority 0.75: Deterministic State Machine Verification
            if not solution_found and "ENTERPRISE WORKFLOW STATE MACHINE" in stimulus:
                from hnsds.verifier.state_machine_solver import StateMachineSolver
                self.sm_engine = StateMachineSolver()
                parsed_sm = self.logic_parser.parse_state_machine(stimulus)
                
                for state in parsed_sm["states"]:
                    self.sm_engine.register_state(state)
                for trans in parsed_sm["transitions"]:
                    self.sm_engine.add_transition(trans["source"], trans["target"])
                for term in parsed_sm["terminal"]:
                    self.sm_engine.add_terminal_state(term)
                for rec in parsed_sm["recovery"]:
                    self.sm_engine.add_recovery_rule(rec["target"], rec["required"])
                for cond in parsed_sm["conditional"]:
                    self.sm_engine.add_conditional_transition(cond["source"], cond["target"])
                for forb in parsed_sm["forbidden"]:
                    self.sm_engine.add_forbidden_direct(forb["source"], forb["target"])
                    
                is_valid = self.sm_engine.verify_trace(parsed_sm["trace"])
                candidate = "VALID" if is_valid else "INVALID"
                solution_found = True
                method = "DETERMINISTIC_GRAPH_TRAVERSAL"

            # Priority 0.9: Constraint Matrix Verification
            if not solution_found and "GLOBAL RESOURCE ALLOCATION MATRIX" in stimulus:
                from hnsds.verifier.constraint_matrix_solver import ConstraintMatrixSolver
                self.cm_engine = ConstraintMatrixSolver()
                parsed_cm = self.logic_parser.parse_constraint_verification(stimulus)
                
                for cap in parsed_cm["capacities"]:
                    self.cm_engine.add_capacity(cap["resource"], cap["capacity"])
                for link in parsed_cm["draw_links"]:
                    self.cm_engine.add_draw_link(link["node"], link["resource"])
                for cons in parsed_cm["capacity_constraints"]:
                    self.cm_engine.add_capacity_constraint(cons["resource"], cons["pct"])
                if parsed_cm["node_limits"] is not None:
                    self.cm_engine.add_node_resource_limit(parsed_cm["node_limits"])
                for p_draw in parsed_cm["proposed_draws"]:
                    self.cm_engine.add_proposed_state_draw(p_draw["node"], p_draw["amount"], p_draw["resource"])
                for p_pct in parsed_cm["proposed_pct_draws"]:
                    self.cm_engine.add_proposed_state_percent_draw(p_pct["node"], p_pct["pct"], p_pct["resource"])
                if parsed_cm["explicit_contradictions"]:
                    self.cm_engine.add_proposed_state_contradiction()
                    
                candidate = self.cm_engine.verify()
                solution_found = True
                method = "DETERMINISTIC_Z3_VERIFICATION"

            # Priority 0.95: Requirements Specification Verification
            if not solution_found and "REQUIREMENTS SPECIFICATION" in stimulus:
                self.requirements_engine = RequirementsSolver()
                parsed_req = self.logic_parser.parse_requirements(stimulus)

                for feat in parsed_req["required"]:
                    self.requirements_engine.require(feat)
                for feat in parsed_req["disabled"]:
                    self.requirements_engine.disable(feat)
                for p in parsed_req["prerequisites"]:
                    self.requirements_engine.add_prerequisite(p["feature"], p["prereq"])
                for mx in parsed_req["mutual_exclusions"]:
                    self.requirements_engine.add_mutual_exclusion(mx["a"], mx["b"])
                for d in parsed_req["dependencies"]:
                    self.requirements_engine.add_dependency(d["dependent"], d["dependency"])
                for ec in parsed_req["explicit_conflicts"]:
                    # Both features are asserted active — Z3 will detect the clash
                    self.requirements_engine.require(ec["a"])
                    self.requirements_engine.require(ec["b"])
                    self.requirements_engine.add_mutual_exclusion(ec["a"], ec["b"])

                result = self.requirements_engine.solve()
                if result.is_valid():
                    candidate = "SATISFIABLE"
                else:
                    kinds = {v.kind.name for v in result.violations}
                    candidate = "|".join(sorted(kinds)) if kinds else "UNSATISFIABLE"
                solution_found = True
                method = "DETERMINISTIC_Z3_VERIFICATION"

            # Priority 1: Mathematical/Logical Reduction (Highest Certainty)
            if not solution_found:
                candidate = self.logic_prover.solve(sigma)
                if candidate and "Solved:" in str(candidate) or "=" in str(candidate):
                    if "Unsolvable" not in str(candidate):
                        solution_found = True
                        method = "REDUCTION"

            # Priority 2: Constraint Satisfaction (Logical Composition)
            if not solution_found:
                parsed_problem = self.logic_parser.parse(sigma.get("problem", str(sigma)))
                candidate = self.csp_engine.solve_csp(parsed_problem)
                if candidate and "FAILED" not in str(candidate):
                    solution_found = True
                    method = "COMPOSITION"


            # Priority 3: Procedural Synthesis (Constructing new logic)
            if not solution_found:
                learned = self.memory_lobe.get_relevant_episodes(str(sigma), top_k=3, threshold=0.7)
                seeded = [ep.get("candidate") for ep in learned if ep.get("success")]
                candidate = self.synthesizer.propose(sigma, examples=seeded)
                method = "SYNTHESIS"

            # 5. VERIFICATION & SELF-CORRECTION LOOP
            if method != "DETERMINISTIC_GRAPH_TRAVERSAL":
                for attempt in range(budget):
                    self.mind.memory_trace.append(f"VERIFYING: {step_name} (via {method})")
                    success, feedback = self.logic_prover.verify(candidate, sigma)
                    
                    if success:
                        solution_found = True
                        break
                    else:
                        self.mind.memory_trace.append(f"REPAIR: Verifier rejected {method} hypothesis. Feedback: {feedback}")
                        if method == "SYNTHESIS":
                            candidate = self.synthesizer.propose(sigma, examples=[f"FIX ERROR: {feedback}"])
                        else: break
            else:
                success = True

            if solution_found:
                self.memory_lobe.log_episode(sigma, candidate, success=True)
                final_results.append(f"[{step_name}] Proven: {candidate}")
            else:
                final_results.append(f"[{step_name}] FAILED to bridge gap.")

        # 6. FINAL STATE SYNTHESIS
        proven_output = "\n".join(final_results)
        self.mind.finalize(proven_output)
        return f"[HSCI] Rationale: {rationale}\n\n" + proven_output
    def get_mind_state(self):
        """
        Extracts the full deliberation report from the active mind.
        """
        return self.mind.get_trace()
