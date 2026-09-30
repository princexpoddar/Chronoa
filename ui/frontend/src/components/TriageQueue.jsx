import React from 'react';
import { AlertTriangle, CheckCircle, Eye, LineChart, FileSignature, MapPin, Calendar, Compass } from 'lucide-react';

export default function TriageQueue({
  tiles,
  onSelectTile,
  onOpenDecisionModal,
  onNavigateTab,
}) {
  const totalBreaches = tiles.filter((t) => t.status === 'ALERT_STOPPING_TIME_REACHED').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* 1. KPI Metric Strip */}
      <div className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-label">Monitored AOI Targets</div>
          <div className="kpi-value">{tiles.length} Sites</div>
          <div className="kpi-sub">Sutlej Basin Corridor (MGRS 43RFQ / 43REQ)</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Ville Boundary Breaches</div>
          <div className="kpi-value" style={{ color: 'var(--saffron)' }}>
            {totalBreaches} Active Alerts
          </div>
          <div className="kpi-sub">Evidence E(t) ≥ 20.0 Threshold</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Mean Detection Latency</div>
          <div className="kpi-value mono" style={{ color: 'var(--green)' }}>
            2.4 Passes
          </div>
          <div className="kpi-sub">Earliest supported observation</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">False Alarm Suppression</div>
          <div className="kpi-value" style={{ color: 'var(--cyan)' }}>
            FAR ≤ 5.0%
          </div>
          <div className="kpi-sub">Ville's inequality martingale guarantee</div>
        </div>
      </div>

      {/* 2. Candidate Cards Grid */}
      <div className="cand-grid">
        {tiles.map((tile, idx) => {
          const isAlert = tile.status === 'ALERT_STOPPING_TIME_REACHED';
          const confPercent = Math.round(tile.confidence * 100);

          return (
            <div
              key={tile.tile_id}
              className={`cand-card ${isAlert ? 'cand-card--alert' : 'cand-card--null'}`}
            >
              <div className="cand-card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="chip" style={{ fontWeight: 700 }}>
                    #{idx + 1}
                  </span>
                  <span className="mono" style={{ fontSize: '0.74rem', color: 'var(--text-1)', fontWeight: 600 }}>
                    {tile.tile_id}
                  </span>
                </div>
                {isAlert ? (
                  <span className="tag tag--saffron">
                    <AlertTriangle size={10} />
                    BREACH: E={tile.e_value.toFixed(1)}
                  </span>
                ) : (
                  <span className="tag tag--muted">
                    <CheckCircle size={10} />
                    H₀ STABLE (E={tile.e_value.toFixed(1)})
                  </span>
                )}
              </div>

              <div className="cand-card-body">
                <div className="cand-title">{tile.description}</div>

                {/* Progress / Confidence */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-2)' }}>Detection Confidence</span>
                    <span className="mono" style={{ fontWeight: 600, color: isAlert ? 'var(--saffron)' : 'var(--text-2)' }}>
                      {confPercent}%
                    </span>
                  </div>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{
                        width: `${confPercent}%`,
                        background: isAlert ? 'var(--saffron)' : 'var(--text-3)',
                      }}
                    />
                  </div>
                </div>

                {/* Metadata Row */}
                <div className="chips">
                  <span className={`tag ${isAlert ? 'tag--saffron' : 'tag--muted'}`}>
                    {tile.change_class.replace(/_/g, ' ')}
                  </span>
                  <span className="chip">MGRS {tile.coordinates.mgrs}</span>
                  <span className="chip">
                    {tile.coordinates.lat.toFixed(4)}°N, {tile.coordinates.lon.toFixed(4)}°E
                  </span>
                </div>

                <div
                  style={{
                    background: 'var(--bg-2)',
                    border: '1px solid var(--border-0)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '6px',
                    fontSize: '0.68rem',
                  }}
                >
                  <div>
                    <span style={{ color: 'var(--text-2)' }}>Observation Window: </span>
                    <span className="mono" style={{ color: 'var(--text-1)' }}>
                      {tile.pre_date} → {tile.post_date}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-2)' }}>DiD Cohort Score: </span>
                    <span className="mono" style={{ color: 'var(--cyan)' }}>
                      {tile.did_score.toFixed(3)}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-2)' }}>Conformal p-value: </span>
                    <span className="mono" style={{ color: tile.p_value < 0.05 ? 'var(--saffron)' : 'var(--green)' }}>
                      p = {tile.p_value.toFixed(4)}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-2)' }}>Earliest Detection τ: </span>
                    <span className="mono" style={{ color: 'var(--text-0)', fontWeight: 600 }}>
                      {tile.stopping_time ? `Pass #${tile.stopping_time}` : 'Not Triggered'}
                    </span>
                  </div>
                </div>

                {/* Action buttons */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px', marginTop: 'auto', paddingTop: '4px' }}>
                  <button
                    className="btn btn--ghost btn--sm"
                    onClick={() => {
                      onSelectTile(tile);
                      onNavigateTab('visualizer');
                    }}
                    title="Inspect bi-temporal multispectral imagery"
                  >
                    <Eye size={12} />
                    Inspect
                  </button>

                  <button
                    className="btn btn--ghost btn--sm"
                    onClick={() => {
                      onSelectTile(tile);
                      onNavigateTab('martingale');
                    }}
                    title="View sequential test martingale trajectory"
                  >
                    <LineChart size={12} />
                    Martingale
                  </button>

                  <button
                    className="btn btn--primary btn--sm"
                    onClick={() => onOpenDecisionModal(tile)}
                    title="Sign and log review decision to SHA-256 audit ledger"
                  >
                    <FileSignature size={12} />
                    Review
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
