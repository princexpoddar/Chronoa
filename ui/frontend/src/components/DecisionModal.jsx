import React, { useState } from 'react';
import { FileSignature, X, ShieldAlert, CheckCircle2, Lock } from 'lucide-react';

export default function DecisionModal({
  tile,
  onClose,
  onDecisionLogged,
}) {
  const [analystId, setAnalystId] = useState('DEFENSE_ANALYST_01');
  const [decision, setDecision] = useState(
    tile?.status === 'ALERT_STOPPING_TIME_REACHED' ? 'VERIFIED' : 'REJECTED'
  );
  const [rationale, setRationale] = useState(
    tile?.status === 'ALERT_STOPPING_TIME_REACHED'
      ? `Stopping time reached (E=${tile.e_value.toFixed(1)} > 20.0). Sub-pixel alignment verified (<0.1px). ST_DWithin waterway buffer confirmed within 500m.`
      : `Harmonic phenological field baseline explains observed spectral variation (p=${tile.p_value.toFixed(3)}). Suppressed as false alarm.`
  );
  const [submitting, setSubmitting] = useState(false);

  if (!tile) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitting(true);

    fetch('http://localhost:8000/audit/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_id: tile.tile_id,
        analyst_id: analystId,
        decision: decision,
        rationale: rationale,
      }),
    })
      .then((r) => r.json())
      .then((resp) => {
        setSubmitting(false);
        onDecisionLogged();
        onClose();
      })
      .catch((err) => {
        console.error('Failed to log audit decision:', err);
        setSubmitting(false);
      });
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title">
            <FileSignature size={16} color="var(--saffron)" />
            <span>Sign & Commit Analyst Provenance Decision (PS §2.2.5)</span>
          </div>
          <button className="btn btn--ghost btn--sm" onClick={onClose} style={{ padding: '4px 6px' }}>
            <X size={14} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {/* Target Card Header */}
            <div
              style={{
                background: 'var(--bg-2)',
                border: '1px solid var(--border-1)',
                borderRadius: 'var(--radius-sm)',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--cyan)' }}>
                  {tile.tile_id}
                </span>
                <span className={`tag ${tile.status.includes('ALERT') ? 'tag--saffron' : 'tag--muted'}`}>
                  E-Value: {tile.e_value.toFixed(1)}
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-1)' }}>
                {tile.description}
              </div>
              <div className="mono" style={{ fontSize: '0.65rem', color: 'var(--text-2)', marginTop: '2px' }}>
                Coordinates: {tile.coordinates.lat.toFixed(4)}°N, {tile.coordinates.lon.toFixed(4)}°E (MGRS: {tile.coordinates.mgrs})
              </div>
            </div>

            {/* Officer ID */}
            <div className="form-group">
              <label className="form-label">Reviewing Officer Call-Sign / ID</label>
              <input
                type="text"
                className="form-input mono"
                value={analystId}
                onChange={(e) => setAnalystId(e.target.value)}
                required
              />
            </div>

            {/* Decision Selector */}
            <div className="form-group">
              <label className="form-label">Analyst Verdict</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <button
                  type="button"
                  className={`btn ${decision === 'VERIFIED' ? 'btn--success' : 'btn--ghost'}`}
                  onClick={() => setDecision('VERIFIED')}
                  style={{ padding: '10px' }}
                >
                  <CheckCircle2 size={14} />
                  VERIFY GENUINE ANOMALY
                </button>
                <button
                  type="button"
                  className={`btn ${decision === 'REJECTED' ? 'btn--danger' : 'btn--ghost'}`}
                  onClick={() => setDecision('REJECTED')}
                  style={{ padding: '10px' }}
                >
                  <ShieldAlert size={14} />
                  REJECT AS FALSE ALARM
                </button>
              </div>
            </div>

            {/* Forensic Rationale */}
            <div className="form-group">
              <label className="form-label">Forensic Rationale & Operational Notes</label>
              <textarea
                className="form-textarea"
                rows={3}
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                required
              />
            </div>

            <div
              style={{
                fontSize: '0.66rem',
                color: 'var(--text-2)',
                background: 'var(--black)',
                padding: '8px 10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-0)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <Lock size={12} color="var(--saffron)" />
              <span>
                Committing will immediately hash this record with the previous block using SHA-256 and store it permanently in the audit chain.
              </span>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn--ghost btn--sm" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn--primary btn--sm" disabled={submitting}>
              {submitting ? 'Writing to Hash Chain...' : 'Commit to SHA-256 Ledger'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
