import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { NotHandledEmail } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function NotHandledEmailsPage() {
  const [emails, setEmails] = useState<NotHandledEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchEmails = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/not-handled-emails`);
      if (!response.ok) throw new Error('Failed to fetch not-handled emails');
      const data = await response.json();
      setEmails(data.emails);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Connection lost. Retrying...');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmails();
    const interval = setInterval(fetchEmails, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleResolve = async (id: string) => {
    setProcessingId(id);
    try {
      const response = await fetch(`${API_BASE}/api/not-handled-emails/${id}/resolve`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(`Failed to resolve request`);
      
      // Update local state immediately
      setEmails((prev) => prev.filter((e) => e.id !== id));
    } catch (err) {
      console.error(err);
      alert(`Error: Could not resolve this request.`);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="layout">
      <nav className="nav">
        <Link to="/" className="nav-link">Customer Portal</Link>
        <Link to="/operator" className="nav-link">Operator Dashboard</Link>
        <Link to="/not-handled" className="nav-link active">Not Handled Emails</Link>
        <Link to="/dashboard" className="nav-link">Manager Dashboard</Link>
        <Link to="/customers" className="nav-link">Customers</Link>
      </nav>

      <main>
        <header>
          <h1>Not Handled Emails</h1>
          <p>Review emails that AI could not process automatically</p>
        </header>

        <section className="card-list" style={{ marginTop: 'var(--spacing-lg)' }}>
          {error && <div className="error-banner">{error}</div>}
          
          {loading && emails.length === 0 ? (
            <div className="empty-state">Loading emails...</div>
          ) : emails.length === 0 ? (
            <div className="empty-state">No pending unhandled emails.</div>
          ) : (
            emails.map((email) => (
              <div key={email.id} className="card">
                <div className="card-header">
                  <span className="chip warning">{email.reason_code}</span>
                  <span className="card-timestamp">{new Date(email.created_at).toLocaleString()}</span>
                </div>
                
                <div className="card-body">
                  <h3 className="card-title">Thread ID: {email.thread_id}</h3>
                  
                  <div className="card-section">
                    <strong>Customer Email Message</strong>
                    <p style={{ margin: 0, fontStyle: 'italic', color: 'var(--text-main)' }}>
                      "{email.original_message}"
                    </p>
                  </div>

                  <div className="card-section highlight">
                    <strong>AI Internal Log (Reason)</strong>
                    <p>{email.ai_log}</p>
                  </div>

                  <div className="chipRow" style={{ marginTop: '8px', marginBottom: 0 }}>
                    <span className="chip info">
                      Intents: {email.detected_intents.length > 0 ? email.detected_intents.join(', ') : 'None'}
                    </span>
                  </div>
                </div>

                <div className="card-actions">
                  <button 
                    className="btn-approve" 
                    onClick={() => handleResolve(email.id)}
                    disabled={processingId === email.id}
                  >
                    {processingId === email.id ? 'Processing...' : 'Mark as Resolved'}
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
