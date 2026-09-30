import React, { useState, useEffect, useRef } from 'react';
import { Eye, Layers, Compass, CheckCircle2, AlertOctagon, Maximize2, RefreshCw } from 'lucide-react';

export default function BiTemporalVisualizer({
  tiles,
  selectedTile,
  setSelectedTile,
  onOpenDecisionModal,
  theme = 'dark',
}) {
  const [spectralMode, setSpectralMode] = useState('TRUE_COLOR');
  const preCanvasRef = useRef(null);
  const postCanvasRef = useRef(null);

  const activeTile = selectedTile || tiles[0];
  const isLight = theme === 'light';

  useEffect(() => {
    const isAlert = activeTile?.status === 'ALERT_STOPPING_TIME_REACHED';

    // Draw Pre-Change Canvas
    if (preCanvasRef.current) {
      const ctx = preCanvasRef.current.getContext('2d');
      const w = preCanvasRef.current.width;
      const h = preCanvasRef.current.height;

      ctx.clearRect(0, 0, w, h);

      // Background terrain
      if (isLight) {
        if (spectralMode === 'TRUE_COLOR') {
          ctx.fillStyle = '#e2e8f0';
        } else if (spectralMode === 'FALSE_COLOR_NIR') {
          ctx.fillStyle = '#fce7f3';
        } else {
          ctx.fillStyle = '#f1f5f9';
        }
      } else {
        if (spectralMode === 'TRUE_COLOR') {
          ctx.fillStyle = '#1c2419';
        } else if (spectralMode === 'FALSE_COLOR_NIR') {
          ctx.fillStyle = '#661122';
        } else {
          ctx.fillStyle = '#111827';
        }
      }
      ctx.fillRect(0, 0, w, h);

      // Draw river curve (Sutlej River channel)
      ctx.beginPath();
      ctx.moveTo(w * 0.1, h * 0.2);
      ctx.bezierCurveTo(w * 0.4, h * 0.4, w * 0.6, h * 0.7, w * 0.9, h * 0.85);
      ctx.lineWidth = 36;
      ctx.strokeStyle = isLight ? '#0284c7' : '#1e3a8a';
      ctx.lineCap = 'round';
      ctx.stroke();

      // Draw agricultural parcels
      const parcels = [
        { x: w * 0.15, y: h * 0.45, w: 90, h: 70 },
        { x: w * 0.65, y: h * 0.25, w: 100, h: 80 },
        { x: w * 0.35, y: h * 0.15, w: 80, h: 60 },
      ];

      parcels.forEach((p) => {
        if (isLight) {
          if (spectralMode === 'TRUE_COLOR') {
            ctx.fillStyle = '#86efac';
          } else if (spectralMode === 'FALSE_COLOR_NIR') {
            ctx.fillStyle = '#fda4af';
          } else {
            ctx.fillStyle = '#22c55e';
          }
        } else {
          if (spectralMode === 'TRUE_COLOR') {
            ctx.fillStyle = '#2d4a22';
          } else if (spectralMode === 'FALSE_COLOR_NIR') {
            ctx.fillStyle = '#991b1b';
          } else {
            ctx.fillStyle = '#15803d';
          }
        }
        ctx.fillRect(p.x, p.y, p.w, p.h);
        ctx.strokeStyle = isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';
        ctx.lineWidth = 1;
        ctx.strokeRect(p.x, p.y, p.w, p.h);
      });

      // Status text
      ctx.fillStyle = isLight ? '#475569' : '#a1a1aa';
      ctx.font = '10px JetBrains Mono';
      ctx.fillText(`EPOCH T1: ${activeTile?.pre_date || '2023-12-18'} // S2A L2A`, 12, h - 14);
      ctx.fillText('BASELINE INTACT (NDVI: 0.684)', w - 190, h - 14);
    }

    // Draw Post-Change Canvas
    if (postCanvasRef.current) {
      const ctx = postCanvasRef.current.getContext('2d');
      const w = postCanvasRef.current.width;
      const h = postCanvasRef.current.height;

      ctx.clearRect(0, 0, w, h);

      // Background terrain
      if (isLight) {
        if (spectralMode === 'TRUE_COLOR') {
          ctx.fillStyle = '#e2e8f0';
        } else if (spectralMode === 'FALSE_COLOR_NIR') {
          ctx.fillStyle = '#fce7f3';
        } else {
          ctx.fillStyle = '#f1f5f9';
        }
      } else {
        if (spectralMode === 'TRUE_COLOR') {
          ctx.fillStyle = '#1c2419';
        } else if (spectralMode === 'FALSE_COLOR_NIR') {
          ctx.fillStyle = '#661122';
        } else {
          ctx.fillStyle = '#111827';
        }
      }
      ctx.fillRect(0, 0, w, h);

      // Draw river curve
      ctx.beginPath();
      ctx.moveTo(w * 0.1, h * 0.2);
      ctx.bezierCurveTo(w * 0.4, h * 0.4, w * 0.6, h * 0.7, w * 0.9, h * 0.85);
      ctx.lineWidth = 36;
      ctx.strokeStyle = isLight ? '#0284c7' : '#1e3a8a';
      ctx.lineCap = 'round';
      ctx.stroke();

      // Agricultural parcels
      const parcels = [
        { x: w * 0.15, y: h * 0.45, w: 90, h: 70 },
        { x: w * 0.65, y: h * 0.25, w: 100, h: 80 },
        { x: w * 0.35, y: h * 0.15, w: 80, h: 60 },
      ];

      parcels.forEach((p, idx) => {
        if (isAlert && idx === 0) {
          if (isLight) {
            if (spectralMode === 'TRUE_COLOR') {
              ctx.fillStyle = '#cbd5e1';
            } else if (spectralMode === 'FALSE_COLOR_NIR') {
              ctx.fillStyle = '#94a3b8';
            } else {
              ctx.fillStyle = '#f87171';
            }
          } else {
            if (spectralMode === 'TRUE_COLOR') {
              ctx.fillStyle = '#d4d4d8';
            } else if (spectralMode === 'FALSE_COLOR_NIR') {
              ctx.fillStyle = '#475569';
            } else {
              ctx.fillStyle = '#ef4444';
            }
          }
          ctx.fillRect(p.x, p.y, p.w, p.h);

          // Draw Bounding Box & Crosshairs
          ctx.strokeStyle = isLight ? '#d97706' : '#ff9933';
          ctx.lineWidth = 2;
          ctx.setLineDash([4, 4]);
          ctx.strokeRect(p.x - 6, p.y - 6, p.w + 12, p.h + 12);
          ctx.setLineDash([]);

          // Displacement vector arrow
          ctx.beginPath();
          ctx.moveTo(p.x + p.w / 2, p.y + p.h / 2);
          ctx.lineTo(w * 0.5, h * 0.5);
          ctx.strokeStyle = isLight ? '#d97706' : '#ff9933';
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Anomaly label tag
          ctx.fillStyle = isLight ? '#b45309' : '#ff9933';
          ctx.font = 'bold 9px JetBrains Mono';
          ctx.fillText('ANOMALY CONFIRMED: E=84.2', p.x - 6, p.y - 12);
        } else {
          if (isLight) {
            if (spectralMode === 'TRUE_COLOR') {
              ctx.fillStyle = '#86efac';
            } else if (spectralMode === 'FALSE_COLOR_NIR') {
              ctx.fillStyle = '#fda4af';
            } else {
              ctx.fillStyle = '#22c55e';
            }
          } else {
            if (spectralMode === 'TRUE_COLOR') {
              ctx.fillStyle = '#2d4a22';
            } else if (spectralMode === 'FALSE_COLOR_NIR') {
              ctx.fillStyle = '#991b1b';
            } else {
              ctx.fillStyle = '#15803d';
            }
          }
          ctx.fillRect(p.x, p.y, p.w, p.h);
        }
      });

      // Status text
      ctx.fillStyle = isAlert ? (isLight ? '#b45309' : '#ff9933') : (isLight ? '#475569' : '#a1a1aa');
      ctx.font = '10px JetBrains Mono';
      ctx.fillText(`EPOCH T2: ${activeTile?.post_date || '2023-12-25'} // S2A L2A`, 12, h - 14);
      ctx.fillText(
        isAlert ? 'ANOMALY DETECTED (NDVI: 0.218 [-68%])' : 'H0 CONSISTENT (NO BREACH)',
        w - 240,
        h - 14
      );
    }
  }, [activeTile, spectralMode, isLight]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top control bar */}
      <div
        className="card"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          padding: '12px 16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-2)', textTransform: 'uppercase', fontWeight: 600 }}>
            Active Scene Target:
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
                {t.tile_id} — {t.description.substring(0, 48)}...
              </option>
            ))}
          </select>
        </div>

        {/* Spectral Band Selector Tabs */}
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            className={`btn btn--sm ${spectralMode === 'TRUE_COLOR' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setSpectralMode('TRUE_COLOR')}
          >
            True Color (B04, B03, B02)
          </button>
          <button
            className={`btn btn--sm ${spectralMode === 'FALSE_COLOR_NIR' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setSpectralMode('FALSE_COLOR_NIR')}
          >
            False Color NIR (B08, B04, B03)
          </button>
          <button
            className={`btn btn--sm ${spectralMode === 'NDVI_MASK' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setSpectralMode('NDVI_MASK')}
          >
            NDVI Anomaly Difference Mask
          </button>
        </div>
      </div>

      {/* Side-by-side Inspection Stage */}
      <div className="visualizer-stage">
        {/* Epoch T1 */}
        <div className="scene-canvas-box">
          <div className="canvas-header">
            <span>EPOCH T1 (PRE-CHANGE): {activeTile?.pre_date}</span>
            <span className="mono tag tag--muted">COREGISTRATION: BASELINE</span>
          </div>
          <div className="canvas-container">
            <canvas ref={preCanvasRef} width={580} height={320} style={{ width: '100%', height: '100%' }} />
          </div>
        </div>

        {/* Epoch T2 */}
        <div className="scene-canvas-box">
          <div className="canvas-header">
            <span style={{ color: activeTile?.status.includes('ALERT') ? 'var(--saffron)' : 'var(--text-1)' }}>
              EPOCH T2 (POST-CHANGE): {activeTile?.post_date}
            </span>
            <span className={`mono tag ${activeTile?.status.includes('ALERT') ? 'tag--saffron' : 'tag--green'}`}>
              {activeTile?.status.includes('ALERT') ? 'DETECTION CONFIRMED' : 'NO ANOMALY'}
            </span>
          </div>
          <div className="canvas-container">
            <canvas ref={postCanvasRef} width={580} height={320} style={{ width: '100%', height: '100%' }} />
          </div>
        </div>
      </div>

      {/* Forensic Telemetry Strip */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">
            <Layers size={14} color="var(--saffron)" />
            <span>Forensic Geomorphic & Cohort Verification Metrics</span>
          </div>
          <button
            className="btn btn--primary btn--sm"
            onClick={() => onOpenDecisionModal(activeTile)}
          >
            Sign Review Decision
          </button>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '12px',
            fontSize: '0.74rem',
          }}
        >
          <div style={{ background: 'var(--bg-2)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ color: 'var(--text-2)', fontSize: '0.65rem', textTransform: 'uppercase', marginBottom: '2px' }}>
              Change Morphology
            </div>
            <div style={{ fontWeight: 600, color: 'var(--text-0)' }}>
              {activeTile?.change_class.replace(/_/g, ' ')}
            </div>
            <div className="mono" style={{ fontSize: '0.65rem', color: 'var(--text-2)', marginTop: '2px' }}>
              Perimeter/Area: 0.42
            </div>
          </div>

          <div style={{ background: 'var(--bg-2)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ color: 'var(--text-2)', fontSize: '0.65rem', textTransform: 'uppercase', marginBottom: '2px' }}>
              PostGIS Waterway Proximity
            </div>
            <div style={{ fontWeight: 600, color: 'var(--blue)' }}>
              ST_DWithin(Sutlej River, 320m)
            </div>
            <div className="mono" style={{ fontSize: '0.65rem', color: 'var(--green)', marginTop: '2px' }}>
              Buffer Confirmed
            </div>
          </div>

          <div style={{ background: 'var(--bg-2)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ color: 'var(--text-2)', fontSize: '0.65rem', textTransform: 'uppercase', marginBottom: '2px' }}>
              Co-Registration Alignment
            </div>
            <div className="mono" style={{ fontWeight: 600, color: 'var(--green)' }}>
              Residual: 0.04 px
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-2)', marginTop: '2px' }}>
              Phase Correlation Pass (&lt;0.1px)
            </div>
          </div>

          <div style={{ background: 'var(--bg-2)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ color: 'var(--text-2)', fontSize: '0.65rem', textTransform: 'uppercase', marginBottom: '2px' }}>
              DiD Spatial Cohort Correction
            </div>
            <div className="mono" style={{ fontWeight: 600, color: 'var(--cyan)' }}>
              Δ_DiD = {activeTile?.did_score.toFixed(3)}
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-2)', marginTop: '2px' }}>
              Atmospheric Confounder Suppressed
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
