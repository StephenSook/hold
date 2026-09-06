import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import { QueryClient } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { MotionConfig } from 'motion/react'
import './styles/index.css'
import { App } from './App'
import { indexedDbPersister } from './offline/persister'

// Answers are cached for ten minutes, which matches the /api/status cache, and kept for a day so
// an offline load still has something true to show with its time printed beside it.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 10 * 60_000, gcTime: 24 * 60 * 60_000, retry: 1, refetchOnWindowFocus: false },
  },
})

const persister = indexedDbPersister()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* reducedMotion="user" drops transform and layout animation for anyone who asked for it,
        and keeps opacity and colour, which is the carve-out WCAG 2.3.3 actually makes. */}
    <MotionConfig reducedMotion="user">
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={{ persister, maxAge: 24 * 60 * 60_000, buster: 'v1' }}
      >
        <HashRouter>
          <App />
        </HashRouter>
      </PersistQueryClientProvider>
    </MotionConfig>
  </StrictMode>,
)
