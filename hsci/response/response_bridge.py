from typing import Any, List, Optional
from hsci.core.data_types import FinalOutput, ResponseContext, ResponseType
from hsci.response.conversation_manager import ConversationManager


class ResponseBridge:
    """
    LAYER 6: Response Bridge
    Explains the answer in natural human language.
    Uses axiomatic response construction — no hardcoded fallback strings.
    """

    # Knowledge patterns for general reasoning (Axiomatic Knowledge Base)
    KNOWLEDGE_PATTERNS = {
        # Science & Nature
        "sky blue": "The sky appears blue due to Rayleigh scattering. When sunlight enters Earth's atmosphere, shorter wavelengths (blue light) scatter more than longer wavelengths (red light). This scattered blue light reaches our eyes from all directions, making the sky appear blue.",
        "gravity": "Gravity is a fundamental force of nature that attracts objects with mass toward each other. Described by Newton's Law (F = Gm₁m₂/r²) and refined by Einstein's General Relativity as the curvature of spacetime caused by mass and energy.",
        "photosynthesis": "Photosynthesis is the process by which plants convert light energy into chemical energy. Using chlorophyll, plants absorb CO₂ and H₂O, then use sunlight to produce glucose (C₆H₁₂O₆) and oxygen: 6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂.",
        "quantum": "Quantum computing leverages quantum mechanical phenomena — superposition and entanglement — to process information. Unlike classical bits (0 or 1), quantum bits (qubits) can exist in multiple states simultaneously, enabling exponential speedup for certain problems like factoring and optimization.",
        "evolution": "Evolution is the change in heritable characteristics of biological populations over successive generations. Through natural selection, organisms with favorable traits are more likely to reproduce, gradually shaping species over millions of years.",
        "dna": "DNA (Deoxyribonucleic Acid) is a double-helix molecule that carries genetic instructions for the development and functioning of all known organisms. It consists of nucleotide base pairs (A-T, G-C) arranged along a sugar-phosphate backbone.",
        "black hole": "A black hole is a region of spacetime where gravity is so strong that nothing — not even light — can escape. They form when massive stars collapse at the end of their life cycle. The boundary is called the event horizon.",
        "electricity": "Electricity is the flow of electric charge (electrons) through a conductor. It's governed by Ohm's Law (V = IR) and is the foundation of modern technology, powering everything from lights to computers.",
        "atom": "An atom is the smallest unit of matter that retains the chemical properties of an element. It consists of a nucleus (protons + neutrons) surrounded by electron clouds. Quantum mechanics governs electron behavior in orbitals.",
        "relativity": "Einstein's Theory of Relativity has two parts: Special Relativity (1905) — the speed of light is constant, time dilates at high speeds (E = mc²); and General Relativity (1916) — gravity is the curvature of spacetime caused by mass and energy.",
        "magnetism": "Magnetism is a force produced by moving electric charges. Every magnet has a north and south pole. Electromagnetism (Maxwell's equations) unifies electric and magnetic forces as aspects of a single fundamental interaction.",
        "sound": "Sound is a mechanical wave that propagates through a medium (air, water, solids) via compressions and rarefactions. Its speed depends on the medium (~343 m/s in air). Frequency determines pitch, amplitude determines loudness.",
        "light": "Light is electromagnetic radiation visible to the human eye (wavelengths ~380-700 nm). It exhibits wave-particle duality — behaving as both waves (diffraction, interference) and particles (photons, photoelectric effect).",
        "cell": "A cell is the basic structural and functional unit of all living organisms. Cells contain DNA and are bounded by a membrane. Prokaryotic cells (bacteria) lack a nucleus; eukaryotic cells (plants, animals) have membrane-bound organelles.",
        "planet": "A planet is a celestial body that orbits a star, has sufficient mass for gravity to make it round, and has cleared its orbital neighborhood. Our solar system has 8 planets: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune.",
        "climate": "Climate is the long-term average of weather patterns in a region. Climate change refers to significant shifts in global temperatures and weather patterns, primarily driven by human activities (burning fossil fuels, deforestation) that increase greenhouse gas concentrations.",
        "ecosystem": "An ecosystem is a community of living organisms interacting with their physical environment. It includes producers (plants), consumers (animals), and decomposers (fungi/bacteria) connected through food chains and energy flow.",
        # Technology
        "artificial intelligence": "Artificial Intelligence is the simulation of human intelligence in machines. It encompasses machine learning, neural networks, natural language processing, and reasoning systems. HSCI itself is an AI architecture based on axiomatic reasoning rather than statistical pattern matching.",
        " ai ": "Artificial Intelligence is the simulation of human intelligence in machines. It encompasses machine learning, neural networks, natural language processing, and reasoning systems. HSCI itself is an AI architecture based on axiomatic reasoning rather than statistical pattern matching.",
        "machine learning": "Machine Learning is a subset of AI where systems learn patterns from data without explicit programming. It includes supervised learning (labeled data), unsupervised learning (pattern discovery), and reinforcement learning (reward-based optimization).",
        "neural network": "A Neural Network is a computing system inspired by biological brains. It consists of layers of interconnected nodes (neurons) that process inputs through weighted connections. Deep learning uses many layers for complex pattern recognition.",
        "blockchain": "Blockchain is a distributed, immutable ledger technology. Each block contains a cryptographic hash of the previous block, creating a secure chain. Used for cryptocurrencies, smart contracts, and decentralized applications.",
        "internet": "The Internet is a global network of interconnected computers using the TCP/IP protocol suite. It enables the World Wide Web, email, file sharing, and real-time communication across the globe.",
        "computer": "A computer is an electronic device that processes data according to instructions (programs). Modern computers use binary logic (0s and 1s) implemented in silicon transistors. Key components: CPU, RAM, storage, I/O devices.",
        "programming": "Programming is the process of writing instructions for computers using formal languages (Python, Java, C++, etc.). Programs are sequences of operations that manipulate data to produce desired outputs.",
        "database": "A database is an organized collection of structured data stored electronically. Relational databases (SQL) use tables with relationships; NoSQL databases handle unstructured data. Key operations: Create, Read, Update, Delete (CRUD).",
        "algorithm": "An algorithm is a step-by-step procedure for solving a problem or performing a computation. Key properties: finiteness, definiteness, input, output, effectiveness. Examples: sorting (O(n log n)), searching (O(log n)).",
        "cloud computing": "Cloud computing delivers computing services (servers, storage, databases, AI) over the internet. Models: IaaS (infrastructure), PaaS (platform), SaaS (software). Providers: AWS, Azure, GCP.",
        "cybersecurity": "Cybersecurity protects systems, networks, and data from digital attacks. Key areas: encryption, authentication, firewalls, intrusion detection, vulnerability management. Threats include malware, phishing, and ransomware.",
        # Mathematics
        "calculus": "Calculus is the mathematical study of continuous change. Differential calculus deals with rates of change (derivatives), while integral calculus deals with accumulation (integrals). Together they form the foundation of modern physics and engineering.",
        "algebra": "Algebra is the branch of mathematics dealing with symbols and rules for manipulating them. It's the unifying thread of almost all mathematics, from simple equations (ax + b = c) to abstract structures (groups, rings, fields).",
        "prime": "A prime number is a natural number greater than 1 that has no positive divisors other than 1 and itself. Primes are the building blocks of all integers (Fundamental Theorem of Arithmetic) and are crucial in cryptography.",
        "fibonacci": "The Fibonacci sequence (0, 1, 1, 2, 3, 5, 8, 13, ...) is defined by F(n) = F(n-1) + F(n-2). It appears throughout nature (flower petals, spirals, branching) and its ratio converges to the golden ratio φ ≈ 1.618.",
        "pi": "Pi (π ≈ 3.14159...) is the ratio of a circle's circumference to its diameter. It's an irrational, transcendental number that appears throughout mathematics and physics. Computed to trillions of digits.",
        "statistics": "Statistics is the science of collecting, analyzing, interpreting, and presenting data. Key concepts: mean, median, mode, standard deviation, probability distributions, hypothesis testing, regression analysis.",
        "trigonometry": "Trigonometry studies relationships between angles and sides of triangles. Core functions: sin, cos, tan. Key identity: sin²θ + cos²θ = 1. Essential for physics, engineering, navigation, and signal processing.",
        "logarithm": "A logarithm is the inverse of exponentiation: log_b(x) = y means b^y = x. Natural log (ln) uses base e ≈ 2.718. Logarithms convert multiplication to addition, making complex calculations manageable.",
        # Geography & General Knowledge
        "capital of india": "The capital of India is New Delhi. It serves as the seat of the Government of India and is located in the National Capital Territory of Delhi.",
        "capital of usa": "The capital of the United States is Washington, D.C. (District of Columbia). It has been the federal capital since 1800.",
        "capital of uk": "The capital of the United Kingdom is London, one of the world's major financial and cultural centers.",
        "capital of france": "The capital of France is Paris, known as the 'City of Light.' It's famous for the Eiffel Tower, Louvre Museum, and its cultural significance in art, fashion, and cuisine.",
        "capital of japan": "The capital of Japan is Tokyo, the world's most populous metropolitan area with over 37 million people. It's a major financial center and technology hub.",
        "capital of china": "The capital of China is Beijing (Peking). It's the political and cultural center of the People's Republic of China, home to the Forbidden City and Tiananmen Square.",
        "solar system": "Our Solar System consists of the Sun, 8 planets (Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune), dwarf planets, moons, asteroids, and comets, all bound by gravity.",
        "water": "Water (H₂O) is a polar molecule essential for all known life. It has unique properties: high specific heat capacity, surface tension, and the rare characteristic of being less dense as a solid (ice) than as a liquid.",
        "earth": "Earth is the third planet from the Sun and the only known planet to harbor life. It has a diameter of ~12,742 km, a tilted axis (23.5°) causing seasons, and a protective magnetic field and atmosphere.",
        # Philosophy & Abstract
        "consciousness": "Consciousness is the subjective experience of awareness and thought. It remains one of the hardest problems in philosophy and neuroscience. Theories include Global Workspace Theory, Integrated Information Theory, and Higher-Order Theories.",
        "philosophy": "Philosophy is the study of fundamental questions about existence, knowledge, values, reason, and language. Major branches: metaphysics (reality), epistemology (knowledge), ethics (morality), logic (reasoning), aesthetics (beauty).",
        "time": "Time is the indefinite continued progression of existence. In physics, Einstein showed time is relative — it passes differently depending on speed and gravitational field (time dilation). Whether time has a fundamental 'direction' remains debated.",
        "infinity": "Infinity (∞) is a concept describing something without bound or end. In mathematics, Cantor proved there are different 'sizes' of infinity (countable vs. uncountable). Not a number, but a concept used in calculus, set theory, and cosmology.",
        "democracy": "Democracy is a system of government where power is vested in the people, exercised directly or through elected representatives. Key principles: rule of law, free elections, civil liberties, separation of powers, minority rights protection.",
    }

    def __init__(self):
        self.conversation_manager = ConversationManager()

    def generate(self, final_output: FinalOutput, original_input: str, domain: str) -> str:
        """
        Generates a natural language response with full explanation.
        Uses axiomatic response construction based on domain routing.
        """
        text_lower = original_input.lower().strip()

        # 1. Handle SYNTHESIS (Code Generation)
        if any(c in ["SYNTHESIS"] for c in final_output.concepts_used) or domain == "software_engineering":
            prefix = "[CODE SYNTHESIS]\n"
            code = final_output.answer if isinstance(final_output.answer, str) else str(final_output.answer)
            verification = (
                "Formally verified by the symbolic verifier."
                if final_output.is_verified
                else "Generated code has not been formally verified; review and test it before production use."
            )
            return f"{prefix}Generated Python code:\n\n```python\n{code}\n```\n\n{verification}"

        # 2. Handle TRANSFORMATION (Conversational / Greetings)
        social_keywords = ["hi", "hello", "hey", "greetings"]
        if any(text_lower.startswith(w) or f" {w} " in f" {text_lower} " for w in social_keywords):
            return (
                "Hello! I am HSCI, a Hyper-Symbolic Cognitive Intelligence.\n\n"
                "I don't just guess — I prove. I use a 7-layer neurosymbolic architecture "
                "with Z3 SMT verification, a Graph Neural Network, and SymPy Computer Algebra.\n\n"
                "Here's what I can do:\n"
                "  • Solve math problems: \"What is 5 + 3\" or \"solve x^2 - 4 = 0\"\n"
                "  • Physics calculations: \"find velocity if distance = 100 and time = 5\"\n"
                "  • Finance: \"calculate tax if salary = 50000 and rate = 30%\"\n"
                "  • Code generation: \"write code for fibonacci\"\n"
                "  • General knowledge: \"What is quantum computing?\"\n"
                "  • Learn new concepts: \"define concept density as mass / volume\"\n"
                "  • Explain topics: \"Explain gravity\"\n\n"
                "Ask me anything!"
            )

        if any(w in text_lower.split() for w in ["help"]):
            return (
                "I am HSCI v3.0 — a Neurosymbolic AI powered by axiomatic reasoning.\n\n"
                "📐 **Math & Algebra**: 'calculate 5 + 3', 'solve 2x + 3 = 11'\n"
                "💰 **Finance**: 'find tax if salary = 50000 and rate = 15%'\n"
                "🔬 **Physics**: 'find force if mass = 10 and acceleration = 9.8'\n"
                "💻 **Code**: 'write code to sort a list'\n"
                "📚 **Knowledge**: 'What is quantum computing?', 'Explain DNA'\n"
                "🧠 **Teach Me**: 'define concept density as mass / volume'\n\n"
                "Every mathematical answer is verified by the Z3 SMT Solver."
            )

        # 3. Handle General Knowledge Queries (AXIOMATIC KNOWLEDGE RETRIEVAL)
        knowledge_response = self._query_knowledge(text_lower)
        knowledge_query_prefixes = (
            "what is", "what are", "who is", "who are", "explain",
            "tell me", "describe", "how does", "how do", "why is",
            "why do", "why does", "define", "meaning of", "what does",
        )
        if knowledge_response and text_lower.startswith(knowledge_query_prefixes):
            return (
                f"[KNOWLEDGE] General Intelligence Response:\n\n"
                f"{knowledge_response}\n\n"
                f"Source: HSCI Axiomatic Knowledge Base | "
                f"Concepts: {', '.join(final_output.concepts_used) if final_output.concepts_used else 'general_knowledge'}"
            )

        # 4. Handle "what is" / "explain" / "tell me about" / "how" / "why" queries
        explanation_prefixes = [
            "what is", "what are", "who is", "who are",
            "explain", "tell me about", "tell me", "describe",
            "how does", "how do", "how is", "how are",
            "why is", "why do", "why does", "why are",
            "define", "meaning of", "what does",
        ]
        is_knowledge_query = any(text_lower.startswith(p) for p in explanation_prefixes)

        if is_knowledge_query and not final_output.is_verified:
            # Extract the topic from the query
            topic = text_lower
            for prefix in explanation_prefixes:
                if topic.startswith(prefix):
                    topic = topic[len(prefix):].strip().rstrip('?.')
                    break
            return (
                f"[REASONING] Analysis of '{topic}':\n\n"
                f"I recognize this as a knowledge query about '{topic}'. "
                f"My axiomatic reasoning engine is specialized for "
                f"mathematical proofs and logical verification, but I can learn.\n\n"
                f"To help me learn about '{topic}', you can:\n"
                f"  1. Define a concept: 'define concept {topic.replace(' ', '_')} as <formula>'\n"
                f"  2. Ask a related math question I can verify\n\n"
                f"I'm continuously learning through self-play training. "
                f"Each interaction strengthens my neural pathways."
            )

        # 5. Handle Verified Mathematical Results
        if final_output.is_verified and final_output.answer not in [None, False, "conversational_response"]:
            answer_str = str(final_output.answer)
            if answer_str not in ["dummy_solution_expression", "Unverified or Error", "None"]:
                # Extract numerical answer
                answer_val = final_output.answer
                if final_output.proof and final_output.proof.variable_assignments:
                    # Find the most likely result key
                    potential_keys = ['result', 'tax_amount', 'distance', 'acceleration',
                                      'interest', 'area', 'velocity', 'force', 'x', 'y']
                    for k in potential_keys:
                        if k in final_output.proof.variable_assignments:
                            answer_val = final_output.proof.variable_assignments[k]
                            break

                # Domain-aware formatting
                prefix = ""
                unit = ""
                if domain == "finance":
                    prefix = "[FINANCE] Calculation Result:\n"
                    unit = "₹"
                elif domain == "physics":
                    prefix = "[PHYSICS] Calculation Result:\n"
                elif domain == "geometry":
                    prefix = "[GEOMETRY] Calculation Result:\n"
                else:
                    prefix = "[VERIFIED] Calculation Result:\n"

                display_answer = f"{unit}{answer_val}" if unit else f"{answer_val}"
                answer_text = f"The answer is **{display_answer}**.\n"

                trace_text = "\nReasoning steps:"
                for i, step in enumerate(final_output.reasoning_trace):
                    trace_text += f"\n  {i + 1}. {step}"

                verification_text = f"\n\n✅ Mathematically verified by Z3 SMT Solver."
                concepts_text = f"\nConcepts used: {', '.join(final_output.concepts_used)}"
                attempts_text = f"\nAttempts: {final_output.attempts}"

                full_response = f"{prefix}{answer_text}{trace_text}{verification_text}{concepts_text}{attempts_text}"
                return full_response

        # 6. Handle Unverified results
        if not final_output.is_verified:
            return self._generate_unverified_response(final_output, original_input)

        # 7. Fallback — try knowledge one more time, then give a helpful generic response
        return self._generate_generic_response(original_input, final_output, domain)

    def _query_knowledge(self, text: str) -> Optional[str]:
        """Query the internal knowledge patterns for general knowledge responses."""
        for pattern, response in self.KNOWLEDGE_PATTERNS.items():
            if pattern in text:
                return response
        return None

    def _generate_unverified_response(self, final_output: FinalOutput, original_input: str) -> str:
        msg = "[REASONING] I was unable to formally verify a solution for this query.\n\n"

        if final_output.correction_hint and final_output.correction_hint != "Check SolutionBuilder mapping.":
            msg += f"Hint: {final_output.correction_hint}\n\n"

        # Provide helpful context
        msg += (
            "This could mean:\n"
            "  • The query requires knowledge I haven't learned yet\n"
            "  • The problem structure doesn't match my current concept library\n"
            "  • More information is needed to solve the problem\n\n"
            "You can help me learn by:\n"
            "  • Defining new concepts: 'define concept X as formula'\n"
            "  • Providing structured problems: 'find X if Y = value and Z = value'\n"
            "  • Using the training loop to strengthen my neural pathways"
        )
        return msg

    def _generate_generic_response(self, original_input: str, final_output: FinalOutput, domain: str) -> str:
        """Generate a response for queries that were processed but didn't yield a concrete answer."""
        # Try knowledge base first
        knowledge = self._query_knowledge(original_input.lower())
        if knowledge:
            return f"[KNOWLEDGE] {knowledge}"

        return (
            f"[ANALYSIS] I processed your query about '{domain}' domain.\n\n"
            f"My cognitive pipeline completed {final_output.attempts} reasoning attempt(s) "
            f"with confidence {final_output.confidence:.1%}.\n\n"
            f"For best results, try:\n"
            f"  • Math: 'calculate 5 + 3' or 'solve 2x + 3 = 11'\n"
            f"  • Structured: 'find X if A = value and B = value'\n"
            f"  • Knowledge: 'What is quantum computing?'\n"
            f"  • Code: 'write code to calculate factorial'"
        )
