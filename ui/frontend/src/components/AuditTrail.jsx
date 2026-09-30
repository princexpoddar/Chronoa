import React, { useState, useEffect } from 'react';
import { ShieldCheck, Lock, Download, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';

export default function AuditTrail({ refreshTrigger }) {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);

  const fetchHistory = () => {
    setLoading(true);
    fetch('http://localhost:8000/audit/history')
      .then((r) => r.json())
      .then((data) => {
        setHistory(data);
        setLoading(false);
        setVerifying(false);
      })
      .catch((err) => {
        console.error('Failed to load audit history:', err);
        setLoading(false);
        setVerifying(false);
      });
  };

  useEffect(() => {
    fetchHistory();
  }, [refreshTrigger]);

  const handleExportJson = () => {
    if (!history) return;
    const blob = new Blob([JSON.stringify(history, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chronos_audit_ledger_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const records = history?.records || [];
  const isValid = history?.chain_valid ?? true;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top Banner */}
      <div
        className="card"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-sm)',
              background: isValid ? 'var(--green-dim)' : 'var(--red-dim)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isValid ? 'var(--green)' : 'var(--red)',
            }}
          >
            <ShieldCheck size={20} />
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-0)' }}>
              SHA-256 Cryptographic Hash-Chained Audit Ledger
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-2)' }}>
              Immutable provenance guarantee for PS §2.2.5. Every analyst decision is cryptographically anchored.
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className={`tag ${isValid ? 'tag--green' : 'tag--red'}`}>
            <Lock size={11} />
            {isValid ? 'CHAIN 100% VERIFIED' : 'TAMPER DETECTED'}
          </span>
          <button
            className="btn btn--ghost btn--sm"
            onClick={() => {
              setVerifying(true);
              fetchHistory();
            }}
            disabled={verifying}
          >
            <RefreshCw size={12} className={verifying ? 'animate-spin' : ''} />
            Verify Chain Now
          </button>
          <button className="btn btn--primary btn--sm" onClick={handleExportJson}>
            <Download size={12} />
            Export Audit Ledger
          </button>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Block #</th>
              <th>Candidate Target ID</th>
              <th>Officer Call-Sign</th>
              <th>Decision</th>
              <th>Forensic Rationale</th>
              <th>Cryptographic Hashes (Prev → Curr)</th>
              <th>Timestamp (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => {
              const isVerified = r.decision === 'VERIFIED';
              return (
                <tr key={i}>
                  <td className="mono" style={{ fontWeight: 700, color: 'var(--text-0)' }}>
                    #{String(r.record_id).padStart(3, '0')}
                  </td>
                  <td className="mono" style={{ fontWeight: 600, color: 'var(--cyan)' }}>
                    {r.candidate_id}
                  </td>
                  <td className="mono" style={{ color: 'var(--text-1)' }}>
                    {r.analyst_id}
                  </td>
                  <td>
                    <span className={`tag ${isVerified ? 'tag--green' : 'tag--red'}`}>
                      {r.decision}
                    </span>
                  </td>
                  <td style={{ maxWidth: 320, lineHeight: 1.35 }}>
                    {r.rationale}
                  </td>
                  <td className="mono" style={{ fontSize: '0.65rem' }}>
                    <div style={{ color: 'var(--text-3)' }}>
                      PREV: {r.prev_hash.substring(0, 16)}...
                    </div>
                    <div style={{ color: 'var(--saffron)', fontWeight: 600 }}>
                      CURR: {r.current_hash.substring(0, 16)}...
                    </div>
                  </td>
                  <td className="mono" style={{ fontSize: '0.68rem', color: 'var(--text-2)', whiteSpace: 'nowrap' }}>
                    {r.timestamp}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
