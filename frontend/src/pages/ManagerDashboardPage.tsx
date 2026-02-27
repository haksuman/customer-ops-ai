import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import type { DashboardResponse } from '../types';

// const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ManagerDashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [window, setWindow] = useState('7d');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/dashboard?window=${window}`);
      if (!response.ok) throw new Error('Failed to fetch dashboard data');
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Connection lost. Retrying...');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [window]);

  if (loading && !data) return <div className="layout">Loading dashboard...</div>;

  return (
    <div className="layout">
      <nav className="nav">
        <Link to="/" className="nav-link">Customer Portal</Link>
        <Link to="/operator" className="nav-link">Operator Dashboard</Link>
        <Link to="/not-handled" className="nav-link">Not Handled Emails</Link>
        <Link to="/dashboard" className="nav-link active">Manager Dashboard</Link>
        <Link to="/customers" className="nav-link">Customers</Link>
      </nav>

      <main>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
          <div>
            <h1>Operational Insights</h1>
            <p>Real-time automation performance metrics</p>
          </div>
          <div className="window-selector">
            <select 
              value={window} 
              onChange={(e) => setWindow(e.target.value)}
              style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', fontWeight: 600 }}
            >
              <option value="today">Today</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
            </select>
          </div>
        </header>

        {error && <div className="error-banner">{error}</div>}

        {data && (
          <>
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', marginBottom: 'var(--spacing-lg)' }}>
              <div className="panel" style={{ textAlign: 'center' }}>
                <h3>Processed</h3>
                <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--primary)' }}>{data.kpis.total_processed}</div>
              </div>
              <div className="panel" style={{ textAlign: 'center' }}>
                <h3>Auto Handled</h3>
                <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#10b981' }}>{data.kpis.auto_handled}</div>
              </div>
              <div className="panel" style={{ textAlign: 'center' }}>
                <h3>Not Handled</h3>
                <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#f59e0b' }}>{data.kpis.manual_forwarded}</div>
              </div>
              <div className="panel" style={{ textAlign: 'center' }}>
                <h3>Automation %</h3>
                <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)' }}>{data.kpis.automation_rate}%</div>
              </div>
            </div>

            <div className="grid">
              <div className="panel">
                <h2>Volume Trends</h2>
                <div style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.timeseries}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Area type="monotone" dataKey="auto_handled" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.6} />
                      <Area type="monotone" dataKey="manual_forwarded" stackId="1" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.6} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="panel">
                <h2>Intent Distribution</h2>
                <div style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.intents} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" />
                      <YAxis dataKey="intent" type="category" width={150} fontSize={12} />
                      <Tooltip />
                      <Bar dataKey="count" fill="var(--primary)" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="panel">
                <h2>Operator Decisions</h2>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: 'Approved', value: data.kpis.approvals },
                          { name: 'Rejected', value: data.kpis.rejections },
                        ]}
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        <Cell fill="#10b981" />
                        <Cell fill="#ef4444" />
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="panel">
                <h2>Manual Fallback Reasons</h2>
                <div style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.reasons}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="reason" fontSize={12} />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
