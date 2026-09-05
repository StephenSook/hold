import { useEffect, useState } from 'react'

const KEY = 'hold.theme'
type Theme = 'dark' | 'light'

function read(): Theme {
  try {
    const stored = localStorage.getItem(KEY)
    if (stored === 'dark' || stored === 'light') return stored
  } catch {
    /* private mode: fall through to the default */
  }
  return 'dark'
}

/**
 * Dark is the production board. Light is the call sheet. Both are real artifacts, so the
 * toggle is named for them rather than for a brightness setting.
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(read)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    try {
      localStorage.setItem(KEY, theme)
    } catch {
      /* private mode: the choice lasts the session */
    }
  }, [theme])

  const next: Theme = theme === 'dark' ? 'light' : 'dark'
  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      className="script-label cursor-pointer text-10 text-bone-faint transition-colors hover:text-bone"
      aria-label={`Switch to the ${next === 'dark' ? 'board' : 'call sheet'} view`}
      title={`Switch to the ${next === 'dark' ? 'board' : 'call sheet'} view`}
    >
      <span className="hidden sm:inline">{next === 'dark' ? 'Board view' : 'Call sheet view'}</span>
      <span className="sm:hidden">{next === 'dark' ? 'Board' : 'Sheet'}</span>
    </button>
  )
}
