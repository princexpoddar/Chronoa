import React, { useState, useEffect } from 'react';
import { Database, HardDrive, CheckCircle2, FileCode, Layers } from 'lucide-react';

export default function SceneArchive() {
  const [scenesData, setScenesData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/scenes')
      .then((r) => r.json())
      .then((data) => {
        setScenesData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load scenes:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-2)' }}>
        Inspecting local Sentinel-2 GeoTIFF archive...
      </div>
    );
  }

  const scenes = scenesData?.scenes || [];
  const totalMb = scenes.reduce((acc, s) => acc + (s.total_size_mb || 0), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Summary Row */}
      <div className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-label">Ingested Sentinel-2 Scenes</div>
          <div className="kpi-value">{scenes.length} Scenes</div>
          <div className="kpi-sub">Sutlej River Basin / Punjab Peri-Urban Corridor</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Total GeoTIFF Volume</div>
          <div className="kpi-value mono" style={{ color: 'var(--saffron)' }}>
            {Math.round(totalMb).toLocaleString()} MB
          </div>
          <div className="kpi-sub">Multi-spectral L2A Bottom-of-Atmosphere</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Spectral Bands Ingested</div>
          <div className="kpi-value mono" style={{ color: 'var(--cyan)' }}>
            B02, B03, B04, B08
          </div>
          <div className="kpi-sub">Blue, Green, Red, Near-Infrared</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Sovereign Air-Gap Status</div>
          <div className="kpi-value" style={{ color: 'var(--green)' }}>
            100% Offline
          </div>
          <div className="kpi-sub">Pre-staged on local disk storage</div>
        </div>
      </div>

      {/* Scenes Table */}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Scene Identifier</th>
              <th>MGRS Tile</th>
              <th>Acquisition Date</th>
              <th>Processing Level</th>
              <th>Spectral Bands Staged</th>
              <th>Local Size</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {scenes.map((s, idx) => (
              <tr key={idx}>
                <td className="mono" style={{ fontWeight: 600, color: 'var(--text-0)' }}>
                  {s.scene_id}
                </td>
                <td className="mono" style={{ color: 'var(--cyan)' }}>
                  {s.mgrs}
                </td>
                <td className="mono" style={{ color: 'var(--text-1)' }}>
                  {s.acquisition_date}
                </td>
                <td>
                  <span className="chip" style={{ color: 'var(--text-0)', fontWeight: 600 }}>
                    {s.level}
                  </span>
                </td>
                <td>
                  <div className="chips">
                    {s.bands.map((b) => (
                      <span key={b} className="chip">
                        {b.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="mono" style={{ color: 'var(--saffron)' }}>
                  {s.total_size_mb} MB
                </td>
                <td>
                  <span className="tag tag--green">
                    <CheckCircle2 size={10} />
                    STAGED
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
