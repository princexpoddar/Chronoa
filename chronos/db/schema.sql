-- CHRONOS PostGIS + pgvector Schema

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- 1. Tiles and Geometry
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tiles (
    tile_id VARCHAR(32) PRIMARY KEY,
    mgrs_tile VARCHAR(16) NOT NULL,
    center_lon DOUBLE PRECISION NOT NULL,
    center_lat DOUBLE PRECISION NOT NULL,
    elevation_m DOUBLE PRECISION DEFAULT 0.0,
    aspect_deg DOUBLE PRECISION DEFAULT 0.0,
    slope_deg DOUBLE PRECISION DEFAULT 0.0,
    relief_class VARCHAR(16) NOT NULL,
    land_cover VARCHAR(32) DEFAULT 'unknown',
    geom GEOMETRY(Polygon, 4326) NOT NULL
);

CREATE INDEX idx_tiles_geom ON tiles USING GIST (geom);
CREATE INDEX idx_tiles_mgrs ON tiles (mgrs_tile);

-- ---------------------------------------------------------------------------
-- 2. Embeddings and Vectors
-- ---------------------------------------------------------------------------
-- We store the season-invariant semantic vector (v_sem), the phenological
-- fingerprint (v_phen), and the sparse DiD residual (r_sparse) for late 
-- interaction/candidate verification.

CREATE TABLE IF NOT EXISTS tile_embeddings (
    tile_id VARCHAR(32) REFERENCES tiles(tile_id) ON DELETE CASCADE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    n_usable_obs INTEGER DEFAULT 0,
    v_sem VECTOR(256),
    v_phen VECTOR(4),
    PRIMARY KEY (tile_id)
);

-- HNSW Index for fast semantic nearest-neighbour search
CREATE INDEX idx_v_sem_hnsw ON tile_embeddings USING hnsw (v_sem vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------------------
-- 3. Observations and Residuals
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS observations (
    obs_id SERIAL PRIMARY KEY,
    tile_id VARCHAR(32) REFERENCES tiles(tile_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    sensor VARCHAR(16) NOT NULL,
    quality_weight DOUBLE PRECISION NOT NULL,
    is_usable BOOLEAN NOT NULL DEFAULT TRUE,
    r_sparse VECTOR(256),  -- Sparse residual vector
    UNIQUE (tile_id, timestamp, sensor)
);

CREATE INDEX idx_obs_tile_time ON observations (tile_id, timestamp);

-- ---------------------------------------------------------------------------
-- 4. Audit Trail (Tamper-Evident Hash Chain)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS audit_trail (
    record_id SERIAL PRIMARY KEY,
    candidate_id VARCHAR(64) NOT NULL,
    analyst_id VARCHAR(64) NOT NULL,
    decision VARCHAR(32) NOT NULL,
    rationale TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    prev_hash VARCHAR(64) NOT NULL,
    current_hash VARCHAR(64) NOT NULL
);

CREATE INDEX idx_audit_candidate ON audit_trail (candidate_id);
CREATE INDEX idx_audit_timestamp ON audit_trail (timestamp);
