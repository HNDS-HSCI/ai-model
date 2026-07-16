class StateMachineSolver:
    """
    Deterministic State Machine Solver.
    Validates execution traces against a defined DFA and its constraints.
    """
    def __init__(self):
        self.states = set()
        self.transitions = {} # src -> set of targets
        self.terminal_states = set()
        self.recovery_rules = {} # target -> required_pass_through
        self.forbidden_direct = set() # set of (src, tgt)
        self.conditional_transitions = set() # set of (src, tgt) requiring token
    
    def register_state(self, state: str):
        self.states.add(state)
        
    def add_transition(self, src: str, tgt: str):
        if src not in self.transitions:
            self.transitions[src] = set()
        self.transitions[src].add(tgt)
        
    def add_terminal_state(self, state: str):
        self.terminal_states.add(state)
        
    def add_recovery_rule(self, target: str, required_state: str):
        self.recovery_rules[target] = required_state
        
    def add_forbidden_direct(self, src: str, tgt: str):
        self.forbidden_direct.add((src, tgt))
        
    def add_conditional_transition(self, src: str, tgt: str):
        self.conditional_transitions.add((src, tgt))

    def verify_trace(self, trace: list) -> bool:
        """
        Verifies if the given trace is valid according to the DFA rules.
        """
        if not trace:
            return True
            
        history = set()
        history.add(trace[0])
        
        for i in range(len(trace) - 1):
            src = trace[i]
            tgt = trace[i+1]
            
            # 1. State existence
            if src not in self.states or tgt not in self.states:
                return False
                
            # 2. Transition exists
            if src not in self.transitions or tgt not in self.transitions[src]:
                return False
                
            # 3. Terminal state violation
            if src in self.terminal_states:
                return False
                
            # 4. Forbidden direct transition
            if (src, tgt) in self.forbidden_direct:
                return False
                
            # 5. Conditional transition (assuming no token provided)
            if (src, tgt) in self.conditional_transitions:
                return False
                
            # 6. Recovery rule
            if tgt in self.recovery_rules:
                req = self.recovery_rules[tgt]
                if req not in history:
                    return False
                    
            history.add(tgt)
            
        return True
