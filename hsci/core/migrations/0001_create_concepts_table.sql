-- Concepts core table
CREATE TABLE IF NOT EXISTS ukm_concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    namespace TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    axiom_type TEXT NOT NULL,
    abstract_rule TEXT,
    z3_template TEXT,
    domain TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('CANDIDATE', 'ACTIVE', 'WEAKENED', 'DEPRECATED', 'ARCHIVED')),
    created_at REAL NOT NULL,
    last_used REAL NOT NULL,
    strength REAL NOT NULL DEFAULT 0.5,
    proof_count INTEGER NOT NULL DEFAULT 0,
    z3_verified INTEGER NOT NULL CHECK (z3_verified IN (0, 1))
);

-- Concept Aliases table (Decoupled lookup)
CREATE TABLE IF NOT EXISTS ukm_concept_aliases (
    concept_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY (concept_id, alias),
    FOREIGN KEY (concept_id) REFERENCES ukm_concepts (id) ON DELETE CASCADE
);

-- Provenance record table
CREATE TABLE IF NOT EXISTS ukm_concept_provenance (
    provenance_id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    acquisition_method TEXT NOT NULL,
    confidence REAL NOT NULL,
    notes TEXT,
    FOREIGN KEY (concept_id) REFERENCES ukm_concepts (id) ON DELETE CASCADE
);

-- Dynamic Metadata table
CREATE TABLE IF NOT EXISTS ukm_concept_metadata (
    concept_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (concept_id, key),
    FOREIGN KEY (concept_id) REFERENCES ukm_concepts (id) ON DELETE CASCADE
);

-- Learned from domains table
CREATE TABLE IF NOT EXISTS ukm_concept_learned_domains (
    concept_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    PRIMARY KEY (concept_id, domain),
    FOREIGN KEY (concept_id) REFERENCES ukm_concepts (id) ON DELETE CASCADE
);

-- Generalizes to table
CREATE TABLE IF NOT EXISTS ukm_concept_generalizes_to (
    concept_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    PRIMARY KEY (concept_id, target_id),
    FOREIGN KEY (concept_id) REFERENCES ukm_concepts (id) ON DELETE CASCADE
);

-- Required entities table
CREATE TABLE IF NOT EXISTS ukm_concept_required_entities (
    concept_id TEXT NOT NULL,
    entity TEXT NOT NULL,
    PRIMARY KEY (concept_id, entity),
    FOREIGN KEY (concept_id) REFERENCES ukm_concepts (id) ON DELETE CASCADE
);

-- Optional entities table
CREATE TABLE IF NOT EXISTS ukm_concept_optional_entities (
    concept_id TEXT NOT NULL,
    entity TEXT NOT NULL,
    PRIMARY KEY (concept_id, entity),
    FOREIGN KEY (concept_id) REFERENCES ukm_concepts (id) ON DELETE CASCADE
);
