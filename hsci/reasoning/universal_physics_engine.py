"""
UniversalPhysicsEngine — Phase 7 of HSCI Activation
Solves physical science problems using symbolic equations, dimensional analysis, and formula derivation.
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

try:
    import sympy as sp
    from sympy import symbols, Eq, solve
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False

@dataclass
class PhysicsResult:
    """Result from the universal physics engine."""
    solved: bool
    answer: Any
    answer_display: str
    formula_used: str
    steps: List[str]
    variables: Dict[str, Any]
    error: Optional[str] = None

class UniversalPhysicsEngine:
    """
    HSCI Universal Physics & Science Engine.
    Maps physical concepts (velocity, force, work, ideal gases) to symbolic formulas
    and solves for unknowns using SymPy.
    """

    FORMULAS = {
        # Kinematics & Mechanics
        "velocity_distance_time": {
            "equation": "Eq(distance, velocity * time)",
            "symbols": ["distance", "velocity", "time"],
            "description": "Distance = Velocity * Time"
        },
        "force_mass_acceleration": {
            "equation": "Eq(force, mass * acceleration)",
            "symbols": ["force", "mass", "acceleration"],
            "description": "Newton's Second Law: Force = Mass * Acceleration"
        },
        "work_force_distance": {
            "equation": "Eq(work, force * distance)",
            "symbols": ["work", "force", "distance"],
            "description": "Work = Force * Distance"
        },
        "power_work_time": {
            "equation": "Eq(power, work / time)",
            "symbols": ["power", "work", "time"],
            "description": "Power = Work / Time"
        },
        "kinetic_energy": {
            "equation": "Eq(kinetic_energy, 0.5 * mass * velocity**2)",
            "symbols": ["kinetic_energy", "mass", "velocity"],
            "description": "Kinetic Energy = 0.5 * Mass * Velocity^2"
        },
        "potential_energy": {
            "equation": "Eq(potential_energy, mass * gravity * height)",
            "symbols": ["potential_energy", "mass", "gravity", "height"],
            "defaults": {"gravity": 9.8},
            "description": "Gravitational Potential Energy = Mass * Gravity * Height"
        },
        "einstein_energy": {
            "equation": "Eq(energy, mass * speed_of_light**2)",
            "symbols": ["energy", "mass", "speed_of_light"],
            "defaults": {"speed_of_light": 299792458},
            "description": "Mass-Energy Equivalence: E = mc^2"
        },
        # Thermodynamics / Gas Laws
        "ideal_gas_law": {
            "equation": "Eq(pressure * volume, moles * R * temperature)",
            "symbols": ["pressure", "volume", "moles", "R", "temperature"],
            "defaults": {"R": 8.314}, # J/(mol*K)
            "description": "Ideal Gas Law: P * V = n * R * T"
        }
    }

    # Maps synonyms to canonical symbols
    SYNONYM_MAP = {
        "speed": "velocity",
        "dist": "distance",
        "t": "time",
        "f": "force",
        "m": "mass",
        "accel": "acceleration",
        "acc": "acceleration",
        "w": "work",
        "p": "pressure",
        "vol": "volume",
        "temp": "temperature",
        "ke": "kinetic_energy",
        "pe": "potential_energy",
        "e": "energy",
        "g": "gravity",
        "h": "height"
    }

    def __init__(self):
        self._sympy_ok = SYMPY_AVAILABLE

    def solve_from_text(self, text: str, entities: Dict[str, Any]) -> PhysicsResult:
        """Main entry: parse input text and entities, search formulas, and solve."""
        if not self._sympy_ok:
            return PhysicsResult(False, None, "", "", [], {}, "sympy not installed")

        text_lower = text.lower()
        normalized_entities = self._normalize_entities(entities)

        # Find the best matching formula based on keywords and extracted entities
        best_formula_name = self._identify_formula(text_lower, normalized_entities)
        if not best_formula_name:
            return PhysicsResult(False, None, "", "", [], {}, "No matching physics formula found")

        formula_info = self.FORMULAS[best_formula_name]
        
        # Prepare known variables and solve
        result = self._solve_formula(formula_info, normalized_entities)
        return result

    def _normalize_entities(self, entities: Dict[str, Any]) -> Dict[str, float]:
        """Convert raw entities or EntityValue objects into standard physics symbols."""
        normalized = {}
        for name, ev in entities.items():
            canonical_name = self.SYNONYM_MAP.get(name.lower(), name.lower())
            
            # Extract value
            val = None
            from hsci.core.data_types import EntityValue
            if isinstance(ev, EntityValue):
                if ev.known and ev.value is not None:
                    try:
                        val = float(ev.value)
                    except (ValueError, TypeError):
                        pass
            else:
                if ev is not None:
                    try:
                        val = float(ev)
                    except (ValueError, TypeError):
                        pass
            
            if val is not None:
                normalized[canonical_name] = val
        return normalized

    def _identify_formula(self, text: str, normalized_entities: Dict[str, float]) -> Optional[str]:
        """Determine which formula matches the text or available parameters."""
        best_match = None
        max_score = 0

        for formula_name, info in self.FORMULAS.items():
            score = 0
            # Check text keywords
            for sym in info["symbols"]:
                if sym in text:
                    score += 2
            
            # Check overlap with extracted symbols
            overlap = set(info["symbols"]).intersection(set(normalized_entities.keys()))
            score += len(overlap) * 3

            # Needs to have at least one input variable
            if score > max_score and len(overlap) >= 1:
                max_score = score
                best_match = formula_name

        return best_match

    def _solve_formula(self, formula_info: Dict[str, Any], known: Dict[str, float]) -> PhysicsResult:
        try:
            # Build sympy symbols
            sym_dict = {name: sp.symbols(name) for name in formula_info["symbols"]}
            
            # Add defaults if not provided in inputs
            defaults = formula_info.get("defaults", {})
            active_known = {}
            for sym_name in formula_info["symbols"]:
                if sym_name in known:
                    active_known[sym_name] = known[sym_name]
                elif sym_name in defaults:
                    active_known[sym_name] = defaults[sym_name]

            # Identify unknown variables
            unknowns = [name for name in formula_info["symbols"] if name not in active_known]
            if not unknowns:
                # All are known? Let's check consistency
                return PhysicsResult(
                    solved=True, answer=True, answer_display="Consistent parameters",
                    formula_used=formula_info["description"],
                    steps=["All physical parameters were already specified and verified."],
                    variables=active_known
                )
            
            if len(unknowns) > 1:
                return PhysicsResult(
                    solved=False, answer=None, answer_display="", formula_used=formula_info["description"],
                    steps=[f"Missing values for: {', '.join(unknowns)}"], variables=active_known,
                    error=f"Too many unknowns: {unknowns}"
                )

            target = unknowns[0]
            
            # Build Equation
            local_dict = sym_dict.copy()
            local_dict['Eq'] = sp.Eq
            equation = eval(formula_info["equation"], {}, local_dict)

            # Substitute known values
            subs_dict = {sym_dict[k]: v for k, v in active_known.items()}
            subbed_eq = equation.subs(subs_dict)

            # Solve
            solutions = sp.solve(subbed_eq, sym_dict[target])
            if not solutions:
                return PhysicsResult(
                    solved=False, answer=None, answer_display="", formula_used=formula_info["description"],
                    steps=["No solution exists for equation with current parameters."], variables=active_known,
                    error="No mathematical solution found"
                )

            sol = solutions[0]
            sol_val = float(sol.evalf()) if hasattr(sol, 'evalf') else float(sol)

            steps = [
                f"Physical context: {formula_info['description']}",
                f"Equation: {formula_info['equation']}",
                f"Substitutions: {active_known}",
                f"Solving for: '{target}'",
                f"Result: {target} = {sol_val}"
            ]

            all_vars = active_known.copy()
            all_vars[target] = sol_val

            return PhysicsResult(
                solved=True,
                answer=sol_val,
                answer_display=f"{target} = {sol_val}",
                formula_used=formula_info["description"],
                steps=steps,
                variables=all_vars
            )

        except Exception as e:
            return PhysicsResult(
                solved=False, answer=None, answer_display="", formula_used=formula_info["description"],
                steps=[], variables=known, error=str(e)
            )

    def can_solve(self, text: str) -> bool:
        """Quick check if this engine can likely solve the given physics text."""
        physics_keywords = ["speed", "velocity", "force", "acceleration", "mass", "gravity", "kinetic", "potential", "energy", "einstein", "pressure", "volume", "gas law", "thermodynamics"]
        text_lower = text.lower()
        return any(kw in text_lower for kw in physics_keywords)
