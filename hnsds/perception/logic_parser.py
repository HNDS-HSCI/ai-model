import re
from typing import Dict, List, Any

class LogicParser:
    """
    Parses natural language logic puzzles into structured constraints.
    Focuses on Entity-Attribute relationships and Positional logic.
    """
    def __init__(self):
        self.entities = set()
        self.attributes = {} # type -> [values]
        self.constraints = []
        
    def parse_graph(self, text):
        """
        Parses V2 Benchmark prompts into deterministic graph structures.
        Returns a dict with nodes, edges, regional_rules, and packages.
        """
        nodes = []
        edges = []
        regional_rules = []
        packages = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Architecture Planning Parsing
            if match := re.search(r"Service ([\w\.-]+) must deploy in region ([\w\.-]+)\.", line):
                nodes.append({"id": match.group(1), "properties": {"region": match.group(2)}})
            elif match := re.search(r"([\w\.-]+) requires ([\w\.-]+) to be healthy", line):
                edges.append({"source": match.group(1), "target": match.group(2)})
            elif match := re.search(r"([\w\.-]+) requires ([\w\.-]+) as a secondary dependency", line):
                edges.append({"source": match.group(1), "target": match.group(2)})
            elif match := re.search(r"Services in ([\w\.-]+) CANNOT depend on services in ([\w\.-]+)", line):
                regional_rules.append({"src_region": match.group(1), "tgt_region": match.group(2)})
            elif match := re.search(r"CRITICAL UPDATE: Service ([\w\.-]+) \(in ([\w\.-]+)\) strongly requires ([\w\.-]+) \(in ([\w\.-]+)\)", line):
                edges.append({"source": match.group(1), "target": match.group(3)})
            elif match := re.search(r"CRITICAL UPDATE: ([\w\.-]+) now requires ([\w\.-]+) to function", line):
                edges.append({"source": match.group(1), "target": match.group(2)})
                
            # Dependency Resolution Parsing
            elif match := re.search(r"Package ([\w\.-]+) v([\w\.-]+) is available", line):
                packages.append({"id": match.group(1), "version": match.group(2)})
            elif match := re.search(r"([\w\.-]+) strictly requires ([\w\.-]+)\.", line):
                edges.append({"source": match.group(1), "target": match.group(2)})
            elif match := re.search(r"([\w\.-]+) also requires ([\w\.-]+)\.", line):
                edges.append({"source": match.group(1), "target": match.group(2)})
            elif match := re.search(r"FATAL: ([\w\.-]+) requires ([\w\.-]+) v([\w\.-]+), which does not exist", line):
                edges.append({"source": match.group(1), "target": match.group(2), "expected_version": match.group(3)})
            elif match := re.search(r"FATAL: ([\w\.-]+) requires ([\w\.-]+)\.", line):
                edges.append({"source": match.group(1), "target": match.group(2)})

        return {
            "nodes": nodes,
            "edges": edges,
            "regional_rules": regional_rules,
            "packages": packages
        }

    def parse_state_machine(self, text):
        """
        Parses V2 Benchmark prompts into deterministic state machine structures.
        """
        parsed = {
            "states": [],
            "transitions": [],
            "terminal": [],
            "recovery": [],
            "forbidden": [],
            "conditional": [],
            "trace": []
        }
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if match := re.search(r"Valid states registered:\s+(.+)", line):
                states_str = match.group(1).replace(".", "")
                parsed["states"] = [s.strip() for s in states_str.split(",") if s.strip()]
            elif match := re.search(r"T\d+:\s+([\w_]+)\s+->\s+([\w_]+)", line):
                parsed["transitions"].append({"source": match.group(1), "target": match.group(2)})
            elif match := re.search(r"Rule \d+: ([\w_]+) is a TERMINAL state", line):
                parsed["terminal"].append(match.group(1))
            elif match := re.search(r"Cannot enter ([\w_]+) without passing through ([\w_]+)", line):
                parsed["recovery"].append({"target": match.group(1), "required": match.group(2)})
            elif match := re.search(r"([\w_]+) to ([\w_]+) is time-bound", line):
                parsed["conditional"].append({"source": match.group(1), "target": match.group(2)})
            elif match := re.search(r"([\w_]+)\s+->\s+([\w_]+) directly is FORBIDDEN", line):
                parsed["forbidden"].append({"source": match.group(1), "target": match.group(2)})
            elif match := re.search(r"EXECUTION TRACE:\s+(.+)", line):
                trace_str = match.group(1).replace(".", "")
                parsed["trace"] = [s.strip() for s in trace_str.split("->") if s.strip()]
                
        return parsed

    def parse_constraint_verification(self, text):
        """
        Parses V2 Benchmark constraint matrices into Z3 deterministic inputs.
        """
        parsed = {
            "capacities": [],
            "draw_links": [],
            "capacity_constraints": [],
            "node_limits": None,
            "proposed_draws": [],
            "proposed_pct_draws": [],
            "explicit_contradictions": False
        }
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if match := re.search(r"Resource ([\w\.-]+) has base capacity (\d+)", line):
                parsed["capacities"].append({"resource": match.group(1), "capacity": int(match.group(2))})
            elif match := re.search(r"Node ([\w\.-]+) draws from ([\w\.-]+)\.", line):
                parsed["draw_links"].append({"node": match.group(1), "resource": match.group(2)})
            elif match := re.search(r"Total draw on ([\w\.-]+) cannot exceed (\d+)% of capacity", line):
                parsed["capacity_constraints"].append({"resource": match.group(1), "pct": int(match.group(2))})
            elif match := re.search(r"node cannot draw from more than (\d+) resources", line):
                parsed["node_limits"] = int(match.group(1))
            elif match := re.search(r"PROPOSED STATE: ([\w\.-]+) draws (\d+) from ([\w\.-]+)", line):
                parsed["proposed_draws"].append({"node": match.group(1), "amount": int(match.group(2)), "resource": match.group(3)})
            elif match := re.search(r"PROPOSED STATE: .* dictates ([\w\.-]+) must draw (\d+)% of ([\w\.-]+), contradicting", line):
                parsed["proposed_pct_draws"].append({"node": match.group(1), "pct": int(match.group(2)), "resource": match.group(3)})
                parsed["explicit_contradictions"] = True
                
        return parsed

    # ------------------------------------------------------------------
    # Compiled regex cache for parse_requirements (initialised once)
    # ------------------------------------------------------------------
    _RE_REQ_FEATURE      = re.compile(r"Feature\s+([\w\.\-]+)\s+is\s+(?:required|enabled)", re.I)
    _RE_REQ_DISABLE      = re.compile(r"Feature\s+([\w\.\-]+)\s+is\s+(?:disabled|not\s+available)", re.I)
    _RE_REQ_REQUIRES     = re.compile(r"([\w\.\-]+)\s+requires?\s+([\w\.\-]+)", re.I)
    _RE_REQ_PREREQ       = re.compile(r"([\w\.\-]+)\s+(?:needs|depends\s+on|prerequisite[:\s]+)\s+([\w\.\-]+)", re.I)
    _RE_REQ_MUTEX        = re.compile(r"([\w\.\-]+)\s+(?:and|AND)\s+([\w\.\-]+)\s+(?:are\s+)?mutually\s+exclusive", re.I)
    _RE_REQ_CONFLICT     = re.compile(r"CONFLICT:\s+([\w\.\-]+)\s+(?:and|AND)\s+([\w\.\-]+)", re.I)
    _RE_REQ_MISSING      = re.compile(r"MISSING[\s_]PREREQ:\s+([\w\.\-]+)\s+(?:for|of|->)\s+([\w\.\-]+)", re.I)
    _RE_REQ_DEP_FAULT    = re.compile(r"DEPENDENCY_FAULT:\s+([\w\.\-]+)\s+->\s+([\w\.\-]+)", re.I)
    _RE_REQ_ENABLE_BLOCK = re.compile(r"ENABLE:\s+([\w\.\-]+)", re.I)
    _RE_REQ_DISABLE_BLOCK= re.compile(r"DISABLE:\s+([\w\.\-]+)", re.I)

    def parse_requirements(self, text: str) -> Dict[str, Any]:
        """
        Parse a REQUIREMENTS SPECIFICATION block into a structured dict.

        Recognised patterns (case-insensitive):
          Feature X is required/enabled      -> required
          Feature X is disabled/not available-> disabled
          X requires Y                       -> dependencies
          X needs/depends on Y               -> prerequisites
          X and Y are mutually exclusive     -> mutual_exclusions
          CONFLICT: X and Y                  -> explicit_conflicts
          ENABLE: X                          -> required (shorthand)
          DISABLE: X                         -> disabled (shorthand)

        Returns
        -------
        {
            "required":          List[str],
            "disabled":          List[str],
            "prerequisites":     List[{"feature": str, "prereq": str}],
            "mutual_exclusions": List[{"a": str, "b": str}],
            "dependencies":      List[{"dependent": str, "dependency": str}],
            "explicit_conflicts":List[{"a": str, "b": str}],
        }
        """
        parsed: Dict[str, Any] = {
            "required":           [],
            "disabled":           [],
            "prerequisites":      [],
            "mutual_exclusions":  [],
            "dependencies":       [],
            "explicit_conflicts": [],
        }

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if m := self._RE_REQ_FEATURE.search(line):
                feat = m.group(1)
                if feat not in parsed["required"]:
                    parsed["required"].append(feat)

            elif m := self._RE_REQ_DISABLE.search(line):
                feat = m.group(1)
                if feat not in parsed["disabled"]:
                    parsed["disabled"].append(feat)

            elif m := self._RE_REQ_ENABLE_BLOCK.search(line):
                feat = m.group(1)
                if feat not in parsed["required"]:
                    parsed["required"].append(feat)

            elif m := self._RE_REQ_DISABLE_BLOCK.search(line):
                feat = m.group(1)
                if feat not in parsed["disabled"]:
                    parsed["disabled"].append(feat)

            elif m := self._RE_REQ_CONFLICT.search(line):
                parsed["explicit_conflicts"].append({"a": m.group(1), "b": m.group(2)})

            elif m := self._RE_REQ_MUTEX.search(line):
                parsed["mutual_exclusions"].append({"a": m.group(1), "b": m.group(2)})

            elif m := self._RE_REQ_MISSING.search(line):
                parsed["prerequisites"].append({"feature": m.group(2), "prereq": m.group(1)})

            elif m := self._RE_REQ_DEP_FAULT.search(line):
                parsed["dependencies"].append({"dependent": m.group(1), "dependency": m.group(2)})

            elif m := self._RE_REQ_PREREQ.search(line):
                parsed["prerequisites"].append({
                    "feature": m.group(1).rstrip(".,;:"),
                    "prereq":  m.group(2).rstrip(".,;:"),
                })

            elif m := self._RE_REQ_REQUIRES.search(line):
                parsed["dependencies"].append({
                    "dependent":  m.group(1).rstrip(".,;:"),
                    "dependency": m.group(2).rstrip(".,;:"),
                })

        return parsed

    def parse(self, text):
        """
        Main entry point. Returns a dictionary of parsed problem structure.
        """
        self.entities = set()
        self.attributes = {}
        self.constraints = []
        
        sentences = text.split('.')
        for sentence in sentences:
            sentence = sentence.strip().lower()
            if not sentence: continue
            
            self._extract_entities_and_types(sentence)
            self._extract_constraints(sentence)
            
        return {
            "entities": list(self.entities),
            "attributes": self.attributes,
            "constraints": self.constraints
        }

    def _extract_entities_and_types(self, sentence):
        # Heuristic: "There are 5 houses" -> Type: House, Count: 5
        # "The Brit lives in the red house" -> Entity: Brit, Attr: Red, Type: House
        
        # Simple noun extraction (very basic)
        words = sentence.split()
        
        # Check for numeric definition
        # e.g. "There are 5 houses"
        match = re.search(r'(\d+) ([a-z]+)s', sentence)
        if match:
            count = int(match.group(1))
            type_name = match.group(2)
            self.attributes[type_name] = [f"{type_name}_{i+1}" for i in range(count)]
            return

    def _extract_constraints(self, sentence):
        # 1. Assignment: "The Brit lives in the Red house"
        # 2. Adjacency: "The Green house is next to the White house"
        # 3. Negation: "The Swede does not keep dogs"
        
        # Normalize
        s = sentence.replace("lives in", "is").replace("keeps", "is").replace("eats", "is").replace("drinks", "is")
        
        # KEYWORD MATCHING
        
        # Negation
        is_negation = "not" in s
        
        # Adjacency
        if "next to" in s or "neighbor" in s:
            parts = re.split(r' next to | neighbor ', s)
            if len(parts) == 2:
                # Cleanup "is" from the end of the subject
                # "The Brit is" -> "The Brit"
                left_raw = re.sub(r'\s+is\s*$', '', parts[0].strip())
                
                left = self._extract_noun(left_raw)
                right = self._extract_noun(parts[1])
                self.constraints.append({
                    "type": "adjacency",
                    "entity1": left,
                    "entity2": right,
                    "negation": is_negation
                })
                return

        # Direct Association (is)
        # We need to be careful not to trigger on "is" inside "is next to" (handled above)
        if " is " in s:
            parts = s.split(" is ")
            left = self._extract_noun(parts[0])
            right = self._extract_noun(parts[1])
            self.constraints.append({
                "type": "association",
                "entity1": left,
                "entity2": right,
                "negation": is_negation
            })
            return

    def _extract_noun(self, phrase):
        # Attempt to get the key noun. 
        # "The red house" -> "red" (if it's a known attribute like color)
        # Heuristic: If we have 2 words, and 2nd is "house/man", take 1st.
        # Else take the whole thing cleaned.
        
        clean = phrase.replace("the", "").replace("a ", "").strip()
        words = clean.split()
        
        # Filter generic containers
        generics = {"house", "man", "person", "pet", "drink"}
        
        if len(words) >= 2 and words[-1] in generics:
            return words[-2] # "red house" -> "red"
            
        return clean.split()[-1] # Fallback to last word if single
