import React, { useState, useEffect } from 'react';
import { Layers, MapPin, Search, Sparkles, Compass, CheckCircle } from 'lucide-react';

export default function DiscoveryClusters({ onSelectTileId, onNavigateTab }) {
  const [clusterData, setClusterData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/clusters')
      .then((r) => r.json())
      .then((data) => {
        setClusterData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load clusters:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-2)' }}>
        Loading HDBSCAN joint embedding clusters...
      </div>
    );
  }

  const clusters = clusterData?.clusters || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header bar */}
      <div className="card">
        <div className="card-head" style={{ marginBottom: 0 }}>
          <div>
            <div className="card-title">
              <Sparkles size={14} color="var(--saffron)" />
              <span>HDBSCAN Unsupervised Representation Clusters (PS §2.2.4)</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-2)', marginTop: '4px' }}>
              Joint representation space [v_sem, v_phen] (d=264). Groups similar anomalous sites across sovereign regions without manual queries.
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span className="chip">Min Cluster Size: 15</span>
            <span className="chip">Dimensions: 264</span>
            <span className="tag tag--saffron">{clusters.length} Clusters Found</span>
          </div>
        </div>
      </div>

      {/* Cluster Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '14px' }}>
        {clusters.map((c) => {
          const isBaseline = c.cluster_id === 0;

          return (
            <div key={c.cluster_id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className={`tag ${isBaseline ? 'tag--muted' : 'tag--saffron'}`}>
                    Cluster #{c.cluster_id}
                  </span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-0)' }}>
                    {c.label}
                  </span>
                </div>
                <span className="mono" style={{ fontSize: '0.74rem', color: isBaseline ? 'var(--text-2)' : 'var(--green)', fontWeight: 600 }}>
                  {Math.round(c.confidence_mean * 100)}% Conf
                </span>
              </div>

              <div style={{ fontSize: '0.74rem', color: 'var(--text-1)', lineHeight: 1.4 }}>
                {c.dominant_phenology}
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
                  <span style={{ color: 'var(--text-2)' }}>Primary MGRS: </span>
                  <span className="mono" style={{ color: 'var(--text-0)' }}>
                    {c.primary_mgrs}
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-2)' }}>Cluster Size: </span>
                  <span className="mono" style={{ color: 'var(--saffron)', fontWeight: 600 }}>
                    {c.tile_count} Tiles
                  </span>
                </div>
                <div style={{ gridColumn: 'span 2' }}>
                  <span style={{ color: 'var(--text-2)' }}>Centroid Location: </span>
                  <span className="mono" style={{ color: 'var(--cyan)' }}>
                    {c.centroid_coords.lat.toFixed(4)}°N, {c.centroid_coords.lon.toFixed(4)}°E
                  </span>
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.66rem', color: 'var(--text-2)', textTransform: 'uppercase', marginBottom: '6px', fontWeight: 600 }}>
                  Exemplar Member Tiles
                </div>
                <div className="chips">
                  {c.member_tiles.map((tId) => (
                    <button
                      key={tId}
                      className="chip"
                      style={{ cursor: 'pointer', background: 'var(--bg-3)' }}
                      onClick={() => {
                        onSelectTileId(tId);
                        onNavigateTab('visualizer');
                      }}
                      title="Inspect this tile in bi-temporal visualizer"
                    >
                      › {tId}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
