import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Customer } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/customers`, {
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const data = await response.json();
      setCustomers(data.customers);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Failed to load customers. Check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  return (
    <div className="layout">
      <nav className="nav">
        <Link to="/" className="nav-link">Customer Portal</Link>
        <Link to="/operator" className="nav-link">Operator Dashboard</Link>
        <Link to="/not-handled" className="nav-link">Not Handled Emails</Link>
        <Link to="/dashboard" className="nav-link">Manager Dashboard</Link>
        <Link to="/customers" className="nav-link active">Customers</Link>
      </nav>

      <main>
        <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <h1>Customers</h1>
            <p>Current customer records from the mock database</p>
          </div>
          <button
            className="btn-approve"
            onClick={fetchCustomers}
            disabled={loading}
            style={{ marginTop: '4px' }}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </header>

        <section style={{ marginTop: 'var(--spacing-lg)' }}>
          {error && <div className="error-banner">{error}</div>}

          {loading && customers.length === 0 ? (
            <div className="empty-state">Loading customers...</div>
          ) : customers.length === 0 ? (
            <div className="empty-state">No customer records found.</div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-panel)', borderBottom: '2px solid var(--border)' }}>
                    <th style={thStyle}>Contract No.</th>
                    <th style={thStyle}>Full Name</th>
                    <th style={thStyle}>Postal Code</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Last Meter Reading (kWh)</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((c, i) => (
                    <tr
                      key={c.id}
                      style={{
                        borderBottom: i < customers.length - 1 ? '1px solid var(--border)' : 'none',
                        background: i % 2 === 0 ? 'transparent' : 'var(--bg-panel)',
                      }}
                    >
                      <td style={tdStyle}>
                        <span className="chip info">{c.contract_number}</span>
                      </td>
                      <td style={tdStyle}>{c.full_name}</td>
                      <td style={tdStyle}>{c.postal_code}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                        {c.last_meter_reading_kwh.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!loading && customers.length > 0 && (
            <p style={{ marginTop: 'var(--spacing-sm)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              {customers.length} record{customers.length !== 1 ? 's' : ''} — data loaded live, no cache
            </p>
          )}
        </section>
      </main>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: '12px 16px',
  textAlign: 'left',
  fontWeight: 600,
  fontSize: '0.8rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: 'var(--text-muted)',
};

const tdStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: '0.9rem',
};
