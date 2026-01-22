-- Thanos Memory V2 - Neon pgvector Schema
-- Run this on your Neon database to set up the schema

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Core memories table (mem0 compatible)
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- Voyage AI voyage-2 dimensions
    memory_type VARCHAR(50),  -- preference, fact, experience, goal, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Extended metadata with heat decay system
CREATE TABLE IF NOT EXISTS memory_metadata (
    memory_id UUID PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
    source VARCHAR(50),           -- hey_pocket, telegram, manual, claude_code
    source_file VARCHAR(255),
    original_timestamp TIMESTAMP,
    client VARCHAR(100),
    project VARCHAR(100),
    tags TEXT[],

    -- Heat Decay System
    heat FLOAT DEFAULT 1.0,           -- Current heat score (0.0 - 2.0)
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INT DEFAULT 0,
    importance FLOAT DEFAULT 1.0,     -- Manual boost for critical items
    pinned BOOLEAN DEFAULT FALSE,     -- Never decays if true

    -- Future: Neo4j integration
    neo4j_node_id VARCHAR(255),

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);

-- Vector similarity search index (IVFFlat for approximate nearest neighbor)
-- Note: Run this after inserting some data for best results
-- CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Heat decay indexes
CREATE INDEX IF NOT EXISTS idx_metadata_heat ON memory_metadata(heat DESC);
CREATE INDEX IF NOT EXISTS idx_metadata_last_accessed ON memory_metadata(last_accessed);
CREATE INDEX IF NOT EXISTS idx_metadata_client ON memory_metadata(client);
CREATE INDEX IF NOT EXISTS idx_metadata_source ON memory_metadata(source);
CREATE INDEX IF NOT EXISTS idx_metadata_pinned ON memory_metadata(pinned) WHERE pinned = TRUE;

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_memories_updated_at ON memories;
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View for easy querying with heat data
CREATE OR REPLACE VIEW memories_with_heat AS
SELECT
    m.id,
    m.user_id,
    m.content,
    m.memory_type,
    m.created_at,
    m.updated_at,
    COALESCE(mm.heat, 1.0) as heat,
    COALESCE(mm.importance, 1.0) as importance,
    COALESCE(mm.access_count, 0) as access_count,
    mm.last_accessed,
    mm.pinned,
    mm.source,
    mm.client,
    mm.project,
    mm.tags
FROM memories m
LEFT JOIN memory_metadata mm ON m.id = mm.memory_id;

-- Grant necessary permissions (adjust role name as needed)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO neondb_owner;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO neondb_owner;
