import { ThemeToggle } from './theme/ThemeProvider'

function App() {
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
          <a className="is-active" href="#overview" aria-current="page">
            Overview
          </a>
          <a href="#activities">Activities</a>
          <a href="#zones">Zones</a>
        </nav>

        <ThemeToggle />
      </header>

      <main id="overview">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Training overview</p>
            <h1>Your effort, in focus.</h1>
          </div>
          <p className="status">
            <span aria-hidden="true" />
            Ready for activity data
          </p>
        </div>

        <section className="empty-state" aria-labelledby="empty-state-title">
          <div className="pulse-glyph" aria-hidden="true">
            <span />
          </div>
          <p className="eyebrow">No sessions synced</p>
          <h2 id="empty-state-title">Start with your latest workout.</h2>
          <p>
            Training load, heart-rate zones, and activity trends will appear
            here once the API returns activity data.
          </p>
        </section>

        <section className="zone-legend" aria-label="Heart rate zone scale">
          <div className="zone-legend__label">
            <span>Heart-rate zones</span>
            <small>Below · Z1–Z5</small>
          </div>
          <div className="zone-scale" aria-hidden="true">
            <span className="zone-below" />
            <span className="zone-z1" />
            <span className="zone-z2" />
            <span className="zone-z3" />
            <span className="zone-z4" />
            <span className="zone-z5" />
          </div>
        </section>
      </main>

      <footer>
        <span>Local dashboard</span>
        <span>v0.1</span>
      </footer>
    </div>
  )
}

export default App
