import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useState,
} from 'react'

type ThemePreference = 'light' | 'dark' | 'system'
type ResolvedTheme = Exclude<ThemePreference, 'system'>

const STORAGE_KEY = 'zepp-training-theme'
const THEME_ORDER: ThemePreference[] = ['system', 'light', 'dark']
const ThemeContext = createContext<{
  preference: ThemePreference
  resolvedTheme: ResolvedTheme
  setPreference: (theme: ThemePreference) => void
} | null>(null)

function readPreference(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === 'light' || stored === 'dark' || stored === 'system'
    ? stored
    : 'system'
}

function systemTheme(): ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const [preference, setPreference] = useState<ThemePreference>(readPreference)
  const [systemPreference, setSystemPreference] =
    useState<ResolvedTheme>(systemTheme)
  const resolvedTheme =
    preference === 'system' ? systemPreference : preference

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const updateSystemPreference = (event: MediaQueryListEvent) => {
      setSystemPreference(event.matches ? 'dark' : 'light')
    }

    query.addEventListener('change', updateSystemPreference)
    return () => query.removeEventListener('change', updateSystemPreference)
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme
    document.documentElement.style.colorScheme = resolvedTheme
    localStorage.setItem(STORAGE_KEY, preference)
  }, [preference, resolvedTheme])

  return (
    <ThemeContext value={{ preference, resolvedTheme, setPreference }}>
      {children}
    </ThemeContext>
  )
}

function useTheme() {
  const theme = useContext(ThemeContext)
  if (!theme) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return theme
}

export function ThemeToggle() {
  const { preference, setPreference } = useTheme()
  const currentIndex = THEME_ORDER.indexOf(preference)
  const nextTheme = THEME_ORDER[(currentIndex + 1) % THEME_ORDER.length]

  return (
    <button
      className="theme-toggle"
      type="button"
      aria-label={`Theme: ${preference}. Switch to ${nextTheme}.`}
      onClick={() => setPreference(nextTheme)}
    >
      <span aria-hidden="true" className="theme-toggle__icon">
        {preference === 'system' ? '◐' : preference === 'light' ? '☼' : '☾'}
      </span>
      <span>{preference}</span>
    </button>
  )
}
