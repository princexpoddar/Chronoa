import React from 'react';
import { Search, Terminal, Sliders, Database, ShieldAlert, CheckCircle2, RotateCcw } from 'lucide-react';

export default function Sidebar({
  searchQuery,
  setSearchQuery,
  onSearch,
  queryPlan,
  compiledSql,
  detectionMode,
  setDetectionMode,
  alpha,
  setAlpha,
  statusFilter,
  setStatusFilter,
  onSelectPreset,
}) {
  const PRESETS = [
    {
      label: 'Newly built structures near Sutlej River',
      query: 'newly built structures near Sutlej River channel',
    },
    {
      label: 'Riparian vegetation clearance along embankment',
      query: 'riparian vegetation clearance along embankment',
    },
    {
      label: 'Linear canal road development corridor',
      query: 'road development corridor adjacent to canal',
    },
    {
      label: 'Seasonal crop phenology vs true disturbance',
      query: 'seasonal crop phenology vs true ground disturbance',
    },
    {
      label: 'Water-extent barrage expansion',
      query: 'water-extent expansion near barrage',
    },
  ];

  return (
    <aside className="sidebar">
      {/* 1. Neuro-Symbolic Query Compiler */}
      <div className="sidebar-section">
        <div className="sidebar-title">
          <span>Query Compiler</span>
          <span className="tag tag--saffron" style={{ fontSize: '0.6rem' }}>
            STAGE 9
          </span>
        </div>

        <form
          className="search-box"
          onSubmit={(e) => {
            e.preventDefault();
            onSearch(searchQuery);
          }}
        >
          <div className="search-input-wrap">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              className="search-input"
              placeholder="e.g. structures near river..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn--primary btn--full btn--sm">
            <Terminal size={13} />
            Compile & Search
          </button>
        </form>

        {queryPlan && (
          <div
            style={{
              background: 'var(--bg-2)',
              border: '1px solid var(--border-1)',
              borderRadius: 'var(--radius-sm)',
              padding: '10px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div
              style={{
                fontSize: '0.65rem',
                color: 'var(--text-2)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                fontWeight: 600,
              }}
            >
              Typed Query Algebra
            </div>
            <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-0)' }}>
              {queryPlan.semantic_target && <span style={{ color: 'var(--cyan)' }}>Sem("{queryPlan.semantic_target}")</span>}
              {queryPlan.change_type && <span style={{ color: 'var(--saffron)' }}> ∧ Chg("{queryPlan.change_type}")</span>}
              {queryPlan.spatial_relation && <span style={{ color: 'var(--blue)' }}> ∧ Spa("{queryPlan.spatial_relation}", {queryPlan.spatial_distance_m}m)</span>}
            </div>

            {compiledSql && (
              <>
                <div
                  style={{
                    fontSize: '0.62rem',
                    color: 'var(--text-2)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    fontWeight: 600,
                    marginTop: '4px',
                  }}
                >
                  PostGIS Pushdown SQL
                </div>
                <div
                  className="mono"
                  style={{
                    fontSize: '0.65rem',
                    color: 'var(--text-1)',
                    background: 'var(--black)',
                    padding: '6px',
                    borderRadius: '3px',
                    wordBreak: 'break-all',
                  }}
                >
                  WHERE {compiledSql}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* 2. Tactical Presets */}
      <div className="sidebar-section">
        <div className="sidebar-title">
          <span>Tactical Scenarios</span>
          <span className="chip">5 Presets</span>
        </div>
        <div className="preset-list">
          {PRESETS.map((p, idx) => (
            <button
              key={idx}
              className="preset-btn"
              onClick={() => onSelectPreset(p.query)}
            >
              › {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* 3. Mathematical Parameters */}
      <div className="sidebar-section">
        <div className="sidebar-title">
          <span>Detection Engine</span>
          <Sliders size={12} color="var(--text-2)" />
        </div>

        <div className="form-group">
          <label className="form-label" style={{ fontSize: '0.68rem' }}>
            Analysis Mode
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
            <button
              className={`btn btn--sm ${detectionMode === 'sequential' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setDetectionMode('sequential')}
            >
              Mode A (Seq)
            </button>
            <button
              className={`btn btn--sm ${detectionMode === 'bitemporal' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setDetectionMode('bitemporal')}
            >
              Mode C (Bi-Temp)
            </button>
          </div>
        </div>

        <div className="form-group" style={{ marginTop: '4px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label className="form-label" style={{ fontSize: '0.68rem' }}>
              Ville FAR Limit (α)
            </label>
            <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--saffron)', fontWeight: 600 }}>
              {alpha.toFixed(2)} → 1/α = {(1 / alpha).toFixed(1)}
            </span>
          </div>
          <input
            type="range"
            min="0.01"
            max="0.10"
            step="0.01"
            value={alpha}
            onChange={(e) => setAlpha(parseFloat(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--saffron)', cursor: 'pointer' }}
          />
          <span style={{ fontSize: '0.62rem', color: 'var(--text-2)' }}>
            Theoretical Bound: P(False Alarm) ≤ {alpha}
          </span>
        </div>
      </div>

      {/* 4. Target Filter */}
      <div className="sidebar-section">
        <div className="sidebar-title">
          <span>Target Filter</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <button
            className={`btn btn--sm ${statusFilter === 'ALL' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setStatusFilter('ALL')}
            style={{ justifyContent: 'space-between' }}
          >
            <span>All Monitored Sites</span>
            <span className="mono">5</span>
          </button>
          <button
            className={`btn btn--sm ${statusFilter === 'ALERT' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setStatusFilter('ALERT')}
            style={{ justifyContent: 'space-between', color: statusFilter === 'ALERT' ? 'var(--black)' : 'var(--saffron)' }}
          >
            <span>Ville Boundary Breached</span>
            <span className="mono">4</span>
          </button>
          <button
            className={`btn btn--sm ${statusFilter === 'NULL' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setStatusFilter('NULL')}
            style={{ justifyContent: 'space-between' }}
          >
            <span>H₀ Phenology Baseline</span>
            <span className="mono">1</span>
          </button>
        </div>
      </div>

      {/* 5. System Sovereignty */}
      <div
        style={{
          marginTop: 'auto',
          padding: '10px',
          background: 'var(--black)',
          border: '1px solid var(--border-0)',
          borderRadius: 'var(--radius-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', fontWeight: 600, color: 'var(--green)' }}>
          <CheckCircle2 size={12} />
          <span>SOVEREIGNTY VERIFIED</span>
        </div>
        <div style={{ fontSize: '0.62rem', color: 'var(--text-2)', lineHeight: 1.4 }}>
          Zero external APIs. All Sentinel-2 L2A rasters, PostGIS pushdown queries, and SHA-256 audit hashing run strictly offline.
        </div>
      </div>
    </aside>
  );
}
