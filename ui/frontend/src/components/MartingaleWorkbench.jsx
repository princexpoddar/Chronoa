import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { Activity, ShieldCheck, AlertCircle, Info, BookOpen } from 'lucide-react';

export default function MartingaleWorkbench({
  tiles,
  selectedTile,
  setSelectedTile,
  alpha = 0.05,
  theme = 'dark',
}) {
  const activeTile = selectedTile || tiles[0];
  const threshold = 1.0 / alpha; // e.g. 20.0

  const isLight = theme === 'light';
  const gridColor = isLight ? '#e2e8f0' : '#1f1f24';
  const axisColor = isLight ? '#94a3b8' : '#52525b';
  const tickColor = isLight ? '#64748b' : '#71717a';
  const tooltipBg = isLight ? '#ffffff' : '#0c0c0e';
  const tooltipBorder = isLight ? '#cbd5e1' : '#2a2a32';
  const tooltipText = isLight ? '#0f172a' : '#f4f4f5';

  // Generate 24 passes of sequential martingale data
  const isAlert = activeTile?.status === 'ALERT_STOPPING_TIME_REACHED';
  const stoppingStep = activeTile?.stopping_time || 16;

  const martingaleData = Array.from({ length: 24 }).map((_, i) => {
    const step = i + 1;
    let ev = 1.0;

    if (isAlert) {
      if (step < 12) {
        ev = Math.max(0.4, 1.0 + Math.sin(step * 1.5) * 0.4);
      } else if (step <= stoppingStep) {
        const progress = (step - 11) / (stoppingStep - 11);
        ev = 1.0 + Math.pow(progress, 2.5) * (threshold + 5);
      } else {
        ev = threshold + 5 + (step - stoppingStep) * 6.5;
      }
    } else {
      ev = Math.max(0.3, 1.0 + Math.sin(step * 0.8) * 0.5);
    }

    return {
      pass: `P-${step}`,
      evidence: parseFloat(ev.toFixed(2)),
      threshold: threshold,
    };
  });

  // Generate harmonic phenology vs observed signal data
  const harmonicData = Array.from({ length: 24 }).map((_, i) => {
    const step = i + 1;
    const baseline = 0.5 + 0.25 * Math.sin((step / 24) * 2 * Math.PI);
    let observed = baseline + Math.sin(step * 2.3) * 0.03;

    if (isAlert && step >= 15) {
      observed = 0.18 + Math.sin(step) * 0.02;
    }

    return {
      pass: `P-${step}`,
      baseline: parseFloat(baseline.toFixed(3)),
      observed: parseFloat(observed.toFixed(3)),
    };
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top selector */}
      <div
        className="card"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-2)', textTransform: 'uppercase', fontWeight: 600 }}>
            Inspecting Sequence:
          </span>
          <select
            className="form-input"
            style={{ padding: '4px 10px', fontSize: '0.76rem', width: 'auto' }}
            value={activeTile?.tile_id}
            onChange={(e) => {
              const found = tiles.find((t) => t.tile_id === e.target.value);
              if (found) setSelectedTile(found);
            }}
          >
            {tiles.map((t) => (
              <option key={t.tile_id} value={t.tile_id}>
                {t.tile_id} — (Current E: {t.e_value.toFixed(1)})
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="mono" style={{ fontSize: '0.74rem', color: 'var(--text-1)' }}>
            Target Significance: <strong style={{ color: 'var(--saffron)' }}>α = {alpha.toFixed(2)}</strong>
          </span>
          <span className="tag tag--saffron">
            VILLE BOUNDARY 1/α = {threshold.toFixed(1)}
          </span>
        </div>
      </div>

      {/* Main Chart 1: Martingale Evidence Trajectory */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">
            <Activity size={14} color="var(--saffron)" />
            <span>Sequential Test Martingale Evidence Trajectory E(t) // {activeTile?.tile_id}</span>
          </div>
          <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-2)' }}>
            Power-Family Betting Factor: κ = 0.50
          </span>
        </div>

        <div style={{ width: '100%', height: 260, marginTop: '8px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={martingaleData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="pass" stroke={axisColor} tick={{ fontSize: 10, fill: tickColor }} />
              <YAxis stroke={axisColor} tick={{ fontSize: 10, fill: tickColor }} />
              <Tooltip
                contentStyle={{
                  background: tooltipBg,
                  border: `1px solid ${tooltipBorder}`,
                  borderRadius: 4,
                  fontSize: 11,
                  fontFamily: 'JetBrains Mono',
                  color: tooltipText,
                }}
              />
              <ReferenceLine
                y={threshold}
                stroke="var(--saffron)"
                strokeDasharray="4 4"
                label={{
                  value: `Ville Boundary (1/α = ${threshold.toFixed(0)})`,
                  fill: 'var(--saffron)',
                  fontSize: 10,
                  position: 'top',
                }}
              />
              <Line
                type="monotone"
                dataKey="evidence"
                stroke={isAlert ? 'var(--green)' : tickColor}
                strokeWidth={2}
                dot={{ r: 3, fill: isAlert ? 'var(--green)' : tickColor }}
                name="Evidence E(t)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Main Chart 2: Harmonic Baseline vs Observed Signal */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">
            <Activity size={14} color="var(--blue)" />
            <span>Harmonic Phenology Baseline f̂(t) vs Observed Satellite Spectral Signal</span>
          </div>
          <span className="mono tag tag--blue" style={{ fontSize: '0.65rem' }}>
            IRLS FOURIER K=3
          </span>
        </div>

        <div style={{ width: '100%', height: 220, marginTop: '8px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={harmonicData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="pass" stroke={axisColor} tick={{ fontSize: 10, fill: tickColor }} />
              <YAxis stroke={axisColor} tick={{ fontSize: 10, fill: tickColor }} domain={[0, 1]} />
              <Tooltip
                contentStyle={{
                  background: tooltipBg,
                  border: `1px solid ${tooltipBorder}`,
                  borderRadius: 4,
                  fontSize: 11,
                  fontFamily: 'JetBrains Mono',
                  color: tooltipText,
                }}
              />
              <Line
                type="monotone"
                dataKey="baseline"
                stroke="var(--blue)"
                strokeDasharray="4 4"
                strokeWidth={2}
                dot={false}
                name="Fitted Phenological Baseline"
              />
              <Line
                type="monotone"
                dataKey="observed"
                stroke="var(--saffron)"
                strokeWidth={2}
                dot={{ r: 2.5, fill: 'var(--saffron)' }}
                name="Observed Spectral Signal"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Mathematical Principles Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
        <div className="card" style={{ padding: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', color: 'var(--saffron)' }}>
            <ShieldCheck size={14} />
            <span style={{ fontSize: '0.74rem', fontWeight: 700, textTransform: 'uppercase' }}>
              Ville's Inequality
            </span>
          </div>
          <div className="mono" style={{ fontSize: '0.68rem', color: 'var(--text-1)', background: 'var(--bg-2)', padding: '6px', borderRadius: '3px', marginBottom: '6px' }}>
            P_H0(sup_t E_t ≥ 1/α) ≤ α
          </div>
          <p style={{ fontSize: '0.68rem', color: 'var(--text-2)', lineHeight: 1.4 }}>
            Guarantees that the False Alarm Rate will not exceed α regardless of monitoring duration or stopping time selection.
          </p>
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', color: 'var(--green)' }}>
            <Activity size={14} />
            <span style={{ fontSize: '0.74rem', fontWeight: 700, textTransform: 'uppercase' }}>
              Power Betting Factor
            </span>
          </div>
          <div className="mono" style={{ fontSize: '0.68rem', color: 'var(--text-1)', background: 'var(--bg-2)', padding: '6px', borderRadius: '3px', marginBottom: '6px' }}>
            ς_κ(p) = κ · p^(κ−1)
          </div>
          <p style={{ fontSize: '0.68rem', color: 'var(--text-2)', lineHeight: 1.4 }}>
            Under H₀ (p ~ U(0,1)), expected betting factor E[ς] = 1 (martingale property). Under genuine change (small p), evidence compounds exponentially.
          </p>
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', color: 'var(--blue)' }}>
            <BookOpen size={14} />
            <span style={{ fontSize: '0.74rem', fontWeight: 700, textTransform: 'uppercase' }}>
              Ledoit-Wolf Shrinkage
            </span>
          </div>
          <div className="mono" style={{ fontSize: '0.68rem', color: 'var(--text-1)', background: 'var(--bg-2)', padding: '6px', borderRadius: '3px', marginBottom: '6px' }}>
            S_t = √(r_t^T Σ̂^(−1) r_t)
          </div>
          <p style={{ fontSize: '0.68rem', color: 'var(--text-2)', lineHeight: 1.4 }}>
            Calculates non-conformity Mahalanobis scores using shrinkage covariance, ensuring robust calibration even with high dimensional embeddings.
          </p>
        </div>
      </div>
    </div>
  );
}
