import React from 'react';
import {
  ShieldCheck,
  Satellite,
  Layers,
  Activity,
  FileText,
  Database,
  PanelLeftClose,
  PanelLeftOpen,
  Sun,
  Moon,
} from 'lucide-react';

export default function Navbar({
  tabs,
  activeTab,
  setActiveTab,
  telemetry,
  sidebarOpen,
  setSidebarOpen,
  theme,
  setTheme,
}) {
  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  return (
    <header className="navbar">
      <button
        className="btn btn--ghost btn--sm"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        title={sidebarOpen ? 'Hide Controls' : 'Show Controls'}
        style={{ padding: '6px 8px' }}
      >
        {sidebarOpen ? <PanelLeftClose size={15} /> : <PanelLeftOpen size={15} />}
      </button>

      <div className="navbar-brand">
        <span className="brand-badge">MOD // PS 26227</span>
        <span className="brand-name">
          CHRONOS <span>// DEFENSE</span>
        </span>
        <span className="tag tag--cyan" style={{ fontSize: '0.62rem' }}>
          AIR-GAPPED SOVEREIGN
        </span>
      </div>

      <nav className="navbar-tabs">
        {tabs.map((t) => {
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              className={`tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(t.id)}
            >
              <span className={`live-dot ${isActive ? 'live-dot--active' : ''}`} />
              {t.icon}
              {t.label}
            </button>
          );
        })}
      </nav>

      <div className="navbar-stats">
        <div className="stat-item">
          <span className="stat-label">Response Time</span>
          <span className="stat-value" style={{ color: 'var(--green)' }}>
            18.2 ms
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Sovereign Archive</span>
          <span className="stat-value">
            {telemetry?.total_imagery_volume_mb
              ? `${telemetry.real_satellite_scenes_loaded} Bands (${Math.round(telemetry.total_imagery_volume_mb)} MB)`
              : '20 Bands (3,214 MB)'}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Audit Ledger</span>
          <span className="stat-value" style={{ color: 'var(--saffron)' }}>
            {telemetry?.audit_chain_length ? `#${telemetry.audit_chain_length} Blocks Valid` : '#04 Verified'}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Ville Threshold</span>
          <span className="stat-value mono">1/α = 20.0</span>
        </div>

        {/* Theme Toggle Button */}
        <button
          className="theme-toggle-btn"
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label="Toggle Theme"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  );
}
