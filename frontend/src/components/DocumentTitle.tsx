import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const APP_TITLE = 'CustomerOpsAi'

const ROUTE_TITLES: Record<string, string> = {
  '/': 'Customer Portal',
  '/operator': 'Operator Dashboard',
  '/not-handled': 'Not Handled Emails',
  '/dashboard': 'Manager Dashboard',
  '/customers': 'Customers',
}

export function DocumentTitle() {
  const { pathname } = useLocation()
  const pageName = ROUTE_TITLES[pathname] ?? 'App'

  useEffect(() => {
    document.title = `${APP_TITLE} - ${pageName}`
  }, [pageName])

  return null
}
