import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { DocumentTitle } from './components/DocumentTitle.tsx'
import OperatorPage from './pages/OperatorPage.tsx'
import NotHandledEmailsPage from './pages/NotHandledEmailsPage.tsx'
import ManagerDashboardPage from './pages/ManagerDashboardPage.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <DocumentTitle />
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/operator" element={<OperatorPage />} />
        <Route path="/not-handled" element={<NotHandledEmailsPage />} />
        <Route path="/dashboard" element={<ManagerDashboardPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
