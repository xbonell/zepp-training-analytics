import { useEffect, useState } from 'react'
import { Activities } from './pages/Activities'
import { ActivityDetail } from './pages/ActivityDetail'
import { Overview } from './pages/Overview'
import { Settings } from './pages/Settings'
import { Zones } from './pages/Zones'
import { ThemeToggle } from './theme/ThemeProvider'

type Route =
  | { name: 'overview' }
  | { name: 'activities'; activityId?: string }
  | { name: 'zones' }
  | { name: 'settings' }

function currentRoute(): Route {
  const route = window.location.hash.slice(1)
  if (route === 'zones') return { name: 'zones' }
  if (route === 'settings') return { name: 'settings' }
  if (route === 'activities') return { name: 'activities' }
  if (route.startsWith('activities/')) {
    try {
      const activityId = decodeURIComponent(route.slice('activities/'.length))
      if (activityId) return { name: 'activities', activityId }
    } catch {
      return { name: 'activities' }
    }
  }
  return { name: 'overview' }
}

function App() {
  const [route, setRoute] = useState<Route>(currentRoute)

  useEffect(() => {
    const handleRouteChange = () => setRoute(currentRoute())
    window.addEventListener('hashchange', handleRouteChange)
    return () => window.removeEventListener('hashchange', handleRouteChange)
  }, [])

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#overview" aria-label="Zepp Training home">
          <span className="brand__mark" aria-hidden="true">
            Z
          </span>
          <span>
            <strong>Zepp Training</strong>
            <small>Analytics</small>
          </span>
        </a>

        <nav className="primary-nav" aria-label="Primary navigation">
          <a
            className={route.name === 'overview' ? 'is-active' : undefined}
            href="#overview"
            aria-current={route.name === 'overview' ? 'page' : undefined}
          >
            Overview
          </a>
          <a
            className={route.name === 'activities' ? 'is-active' : undefined}
            href="#activities"
            aria-current={route.name === 'activities' ? 'page' : undefined}
          >
            Activities
          </a>
          <a
            className={route.name === 'zones' ? 'is-active' : undefined}
            href="#zones"
            aria-current={route.name === 'zones' ? 'page' : undefined}
          >
            Zones
          </a>
          <a
            className={route.name === 'settings' ? 'is-active' : undefined}
            href="#settings"
            aria-current={route.name === 'settings' ? 'page' : undefined}
          >
            Settings
          </a>
        </nav>

        <ThemeToggle />
      </header>

      <main id={route.name}>
        {route.name === 'overview' && <Overview />}
        {route.name === 'activities' &&
          (route.activityId ? (
            <ActivityDetail activityId={route.activityId} />
          ) : (
            <Activities />
          ))}
        {route.name === 'zones' && <Zones />}
        {route.name === 'settings' && <Settings />}
      </main>

      <footer>
        <span>Local dashboard</span>
        <span>v0.1</span>
      </footer>
    </div>
  )
}

export default App
