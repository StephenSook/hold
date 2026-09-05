import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Gate } from './components/Gate'
import { Header } from './components/Header'
import { Footer } from './components/Footer'
import { useSmoothScroll } from './hooks/useSmoothScroll'

const Landing = lazy(() => import('./pages/Landing').then((m) => ({ default: m.Landing })))
const BoardPage = lazy(() => import('./pages/BoardPage').then((m) => ({ default: m.BoardPage })))
const DayPage = lazy(() => import('./pages/DayPage').then((m) => ({ default: m.DayPage })))
const ImportPage = lazy(() => import('./pages/ImportPage').then((m) => ({ default: m.ImportPage })))
const JudgePage = lazy(() => import('./pages/JudgePage').then((m) => ({ default: m.JudgePage })))

export function App() {
  const { pathname } = useLocation()
  // Smoothed scroll is for the reading route only. The board is a working surface and an
  // assistant director dragging a strip needs the page to answer the wheel exactly.
  useSmoothScroll(pathname === '/')

  return (
    <>
      <a
        href="#main"
        className="sr-only-focusable script-label fixed top-3 left-3 z-[300] bg-bone px-3 py-2 text-11 text-board"
      >
        Skip to content
      </a>
      <Gate />
      <Header />
      <main id="main" tabIndex={-1} className="min-h-[60vh] outline-none">
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/board" element={<BoardPage />} />
            <Route path="/day/:day" element={<DayPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/judge" element={<JudgePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
      <Footer />
    </>
  )
}

function RouteFallback() {
  return (
    <div className="mx-auto max-w-[1440px] px-5 py-24 sm:px-8">
      <p className="script-label text-11 text-bone-faint">Loading</p>
    </div>
  )
}
