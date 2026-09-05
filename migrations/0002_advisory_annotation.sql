ALTER TABLE decisions ADD COLUMN advisory_rationale TEXT;
ALTER TABLE decisions ADD COLUMN advisory_confidence TEXT
    CHECK (advisory_confidence IS NULL OR advisory_confidence IN ('low', 'medium', 'high'));
ALTER TABLE decisions ADD COLUMN advisory_provider TEXT;
ALTER TABLE decisions ADD COLUMN advisory_cache_key TEXT;
