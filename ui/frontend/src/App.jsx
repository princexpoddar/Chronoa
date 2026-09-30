import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import TriageQueue from './components/TriageQueue';
import BiTemporalVisualizer from './components/BiTemporalVisualizer';
import MartingaleWorkbench from './components/MartingaleWorkbench';
import DiscoveryClusters from './components/DiscoveryClusters';
import AuditTrail from './components/AuditTrail';
import SceneArchive from './components/SceneArchive';
import DecisionModal from './components/DecisionModal';
import { Layers, Eye, Activity, Sparkles, ShieldCheck, Database } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const TABS = [
  { id: 'triage', label: 'Target Triage', icon: <Layers size={14} /> },
  { id: 'visualizer', label: 'Bi-Temporal Visualizer', icon: <Eye size={14} /> },
  { id: 'martingale', label: 'Martingale E-Process', icon: <Activity size={14} /> },
  { id: 'clusters', label: 'HDBSCAN Discovery', icon: <Sparkles size={14} /> },
  { id: 'audit', label: 'SHA-256 Audit Trail', icon: <ShieldCheck size={14} /> },
  { id: 'archive', label: 'Sentinel-2 Archive', icon: <Database size={14} /> },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('triage');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Theme state: 'dark' | 'light'
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('chronos_theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('chronos_theme', theme);
  }, [theme]);

  // Search & Query state
  const [searchQuery, setSearchQuery] = useState('');
  const [queryPlan, setQueryPlan] = useState(null);
  const [compiledSql, setCompiledSql] = useState(null);

  // Detection parameters
  const [detectionMode, setDetectionMode] = useState('sequential'); // 'sequential' | 'bitemporal'
  const [alpha, setAlpha] = useState(0.05);
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL' | 'ALERT' | 'NULL'

  // Data state
  const [tiles, setTiles] = useState([]);
  const [selectedTile, setSelectedTile] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(false);

  // Modals & triggers
  const [decisionModalTile, setDecisionModalTile] = useState(null);
  const [auditRefreshTrigger, setAuditRefreshTrigger] = useState(0);

  // Initial load
  const fetchTelemetry = () => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then(setTelemetry)
      .catch((err) => console.error('Error fetching telemetry:', err));
  };

  const handleSearch = useCallback((query = '') => {
    setLoading(true);
    fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, limit: 100 }),
    })
      .then((r) => r.json())
      .then((data) => {
        setTiles(data.tiles || []);
        if (data.tiles && data.tiles.length > 0 && !selectedTile) {
          setSelectedTile(data.tiles[0]);
        }
        setQueryPlan(data.parsed_plan);
        setCompiledSql(data.compiled_sql);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error searching:', err);
        setLoading(false);
      });
  }, [selectedTile]);

  useEffect(() => {
    fetchTelemetry();
    handleSearch('');
  }, []);

  const handleSelectPreset = (presetQuery) => {
    setSearchQuery(presetQuery);
    handleSearch(presetQuery);
  };

  // Filter tiles based on statusFilter
  const filteredTiles = tiles.filter((t) => {
    if (statusFilter === 'ALERT') return t.status === 'ALERT_STOPPING_TIME_REACHED';
    if (statusFilter === 'NULL') return t.status !== 'ALERT_STOPPING_TIME_REACHED';
    return true;
  });

  return (
    <div className="app" data-theme={theme}>
      <Navbar
        tabs={TABS}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        telemetry={telemetry}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        theme={theme}
        setTheme={setTheme}
      />

      <main className="page">
        <div className={`workspace ${!sidebarOpen ? 'workspace--collapsed' : ''}`}>
          {sidebarOpen && (
            <Sidebar
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              onSearch={handleSearch}
              queryPlan={queryPlan}
              compiledSql={compiledSql}
              detectionMode={detectionMode}
              setDetectionMode={setDetectionMode}
              alpha={alpha}
              setAlpha={setAlpha}
              statusFilter={statusFilter}
              setStatusFilter={setStatusFilter}
              onSelectPreset={handleSelectPreset}
            />
          )}

          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            {activeTab === 'triage' && (
              <TriageQueue
                tiles={filteredTiles}
                onSelectTile={(tile) => {
                  setSelectedTile(tile);
                }}
                onOpenDecisionModal={(tile) => setDecisionModalTile(tile)}
                onNavigateTab={(tab) => setActiveTab(tab)}
              />
            )}

            {activeTab === 'visualizer' && (
              <BiTemporalVisualizer
                tiles={tiles}
                selectedTile={selectedTile}
                setSelectedTile={setSelectedTile}
                onOpenDecisionModal={(tile) => setDecisionModalTile(tile)}
                theme={theme}
              />
            )}

            {activeTab === 'martingale' && (
              <MartingaleWorkbench
                tiles={tiles}
                selectedTile={selectedTile}
                setSelectedTile={setSelectedTile}
                alpha={alpha}
                theme={theme}
              />
            )}

            {activeTab === 'clusters' && (
              <DiscoveryClusters
                onSelectTileId={(tileId) => {
                  const found = tiles.find((t) => t.tile_id === tileId);
                  if (found) setSelectedTile(found);
                }}
                onNavigateTab={(tab) => setActiveTab(tab)}
              />
            )}

            {activeTab === 'audit' && (
              <AuditTrail refreshTrigger={auditRefreshTrigger} />
            )}

            {activeTab === 'archive' && <SceneArchive />}
          </div>
        </div>
      </main>

      {/* Decision Sign-off Modal */}
      {decisionModalTile && (
        <DecisionModal
          tile={decisionModalTile}
          onClose={() => setDecisionModalTile(null)}
          onDecisionLogged={() => {
            setAuditRefreshTrigger((prev) => prev + 1);
            fetchTelemetry();
          }}
        />
      )}
    </div>
  );
}
