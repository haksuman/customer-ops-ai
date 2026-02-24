import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { PendingApproval } from '../types';

export default function OperatorPage() {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchApprovals = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/approvals');
      if (!response.ok) throw new Error('Failed to fetch approvals');
      const data = await response.json();
      setApprovals(data.approvals);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Connection lost. Retrying...');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (id: string, action: 'approve' | 'reject') => {
    setProcessingId(id);
    try {
      const response = await fetch(`http://localhost:8000/api/approvals/${id}/${action}`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(`Failed to ${action} request`);
      
      // Update local state immediately for better UX
      setApprovals((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      console.error(err);
      alert(`Error: Could not ${action} this request.`);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="app-container">
      <nav className="nav">
        <Link to="/" className="nav-link">Customer Portal</Link>
        <Link to="/operator" className="nav-link active">Operator Dashboard</Link>
      </nav>

      <main className="main">
        <header className="header">
          <h1>Operator Approval Dashboard</h1>
          <p className="subtitle">Review and authorize sensitive customer requests</p>
        </header>

        <section className="panel">
          {error && <div className="error-banner">{error}</div>}
          
          {loading && approvals.length === 0 ? (
            <div className="empty-state">Loading approvals...</div>
          ) : approvals.length === 0 ? (
            <div className="empty-state">No pending approval requests.</div>
          ) : (
            <div className="approval-list">
              {approvals.map((approval) => (
                <div key={approval.id} className={`approval-card ${approval.is_dangerous ? 'dangerous' : ''}`}>
                  <div className="approval-header">
                    <span className="intent-badge">{approval.intent}</span>
                    <span className="timestamp">{new Date(approval.created_at).toLocaleString()}</span>
                  </div>
                  
                  <div className="approval-body">
                    <h3>{approval.contract_number}</h3>
                    
                    {approval.customer_info && (
                      <div className="customer-info-box">
                        <strong>Current Customer Record:</strong>
                        <div className="info-grid">
                          <div><span>Name:</span> {approval.customer_info.full_name as string}</div>
                          <div><span>Postal Code:</span> {approval.customer_info.postal_code as string}</div>
                          <div><span>Meter Reading:</span> {approval.customer_info.last_meter_reading_kwh as number} kWh</div>
                        </div>
                      </div>
                    )}

                    <p className="summary"><strong>AI Summary:</strong> {approval.ai_summary}</p>
                    
                    <div className="changes">
                      <strong>Requested Changes:</strong>
                      <pre>{JSON.stringify(approval.requested_change, null, 2)}</pre>
                    </div>

                    {approval.is_dangerous && (
                      <div className="dangerous-badge">⚠️ POTENTIAL RISK DETECTED</div>
                    )}
                  </div>

                  <div className="approval-actions">
                    <button 
                      className="action-btn approve" 
                      onClick={() => handleAction(approval.id, 'approve')}
                      disabled={processingId === approval.id}
                    >
                      {processingId === approval.id ? 'Processing...' : 'Approve'}
                    </button>
                    <button 
                      className="action-btn reject" 
                      onClick={() => handleAction(approval.id, 'reject')}
                      disabled={processingId === approval.id}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
