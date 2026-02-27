import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { PendingApproval } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function OperatorPage() {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchApprovals = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/approvals`);
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
      const response = await fetch(`${API_BASE}/api/approvals/${id}/${action}`, {
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
    <div className="layout">
      <nav className="nav">
        <Link to="/" className="nav-link">Customer Portal</Link>
        <Link to="/operator" className="nav-link active">Operator Dashboard</Link>
        <Link to="/not-handled" className="nav-link">Not Handled Emails</Link>
        <Link to="/dashboard" className="nav-link">Manager Dashboard</Link>
        <Link to="/customers" className="nav-link">Customers</Link>
      </nav>

      <main>
        <header>
          <h1>Operator Approval Dashboard</h1>
          <p>Review and authorize sensitive customer requests</p>
        </header>

        <section className="card-list" style={{ marginTop: 'var(--spacing-lg)' }}>
          {error && <div className="error-banner">{error}</div>}
          
          {loading && approvals.length === 0 ? (
            <div className="empty-state">Loading approvals...</div>
          ) : approvals.length === 0 ? (
            <div className="empty-state">No pending approval requests.</div>
          ) : (
            approvals.map((approval) => (
              <div key={approval.id} className={`card ${approval.is_dangerous ? 'dangerous' : ''}`}>
                <div className="card-header">
                  <span className="chip info">{approval.intent}</span>
                  <span className="card-timestamp">{new Date(approval.created_at).toLocaleString()}</span>
                </div>
                
                <div className="card-body">
                  <h3 className="card-title">Contract: {approval.contract_number}</h3>
                  
                  {approval.customer_info && (
                    <div className="card-section">
                      <strong>Current Customer Record</strong>
                      <div className="info-grid">
                        <div><span>Name:</span> {approval.customer_info.full_name as string}</div>
                        <div><span>Postal Code:</span> {approval.customer_info.postal_code as string}</div>
                        <div><span>Meter Reading:</span> {approval.customer_info.last_meter_reading_kwh as number} kWh</div>
                      </div>
                    </div>
                  )}

                  <div className="card-section">
                    <strong>AI Summary</strong>
                    <p style={{ margin: 0 }}>{approval.ai_summary}</p>
                  </div>
                  
                  <div className="card-section">
                    <strong>Requested Changes</strong>
                    <pre style={{ margin: '8px 0 0', fontSize: '0.8rem', color: 'var(--text-main)', whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(approval.requested_change, null, 2)}
                    </pre>
                  </div>

                  {approval.is_dangerous && (
                    <div className="dangerous-badge">⚠️ POTENTIAL RISK DETECTED</div>
                  )}
                </div>

                <div className="card-actions">
                  <button 
                    className="btn-approve" 
                    onClick={() => handleAction(approval.id, 'approve')}
                    disabled={processingId === approval.id}
                  >
                    {processingId === approval.id ? 'Processing...' : 'Approve'}
                  </button>
                  <button 
                    className="btn-reject" 
                    onClick={() => handleAction(approval.id, 'reject')}
                    disabled={processingId === approval.id}
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))
          )}
        </section>
      </main>
    </div>
  );
}
