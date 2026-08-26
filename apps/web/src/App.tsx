import { useEffect, useState } from 'react'
import { Activities } from './pages/Activities'
import { Overview } from './pages/Overview'
import { ThemeToggle } from './theme/ThemeProvider'

type Route = 'overview' | 'activities' | 'zones'

function currentRoute(): Route {
  const route = window.location.hash.slice(1)
  return route === 'activities' || route === 'zones' ? route : 'overview'
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
            className={route === 'overview' ? 'is-active' : undefined}
            href="#overview"
            aria-current={route === 'overview' ? 'page' : undefined}
          >
            Overview
          </a>
          <a
            className={route === 'activities' ? 'is-active' : undefined}
            href="#activities"
            aria-current={route === 'activities' ? 'page' : undefined}
          >
            Activities
          </a>
          <a
            className={route === 'zones' ? 'is-active' : undefined}
            href="#zones"
            aria-current={route === 'zones' ? 'page' : undefined}
          >
            Zones
          </a>
        </nav>

        <ThemeToggle />
      </header>

      <main id={route}>
        {route === 'overview' && <Overview />}
        {route === 'activities' && <Activities />}
        {route === 'zones' && (
          <section className="empty-state">
            <p className="eyebrow">Heart-rate profile</p>
            <h1>Zones</h1>
            <p>Zone configuration arrives in the next dashboard view.</p>
          </section>
        )}
      </main>

      <footer>
        <span>Local dashboard</span>
        <span>v0.1</span>
      </footer>
    </div>
  )
}

export default App
