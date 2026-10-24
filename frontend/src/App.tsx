import { useState } from 'react'
import Decision from './pages/Decision'

type Tab = 'Decision' | 'Accuracy'

export default function App() {
  const [tab, setTab] = useState<Tab>('Decision')
  return (
    <div className="app">
      <nav className="tabs" aria-label="Section">
        <button
          className={`tab ${tab === 'Decision' ? 'active' : ''}`}
          onClick={() => setTab('Decision')}
        >
          Decision
        </button>
        <button
          className="tab"
          aria-disabled="true"
          disabled
          onClick={() => setTab('Accuracy')}
        >
          Accuracy &mdash; coming in M5
        </button>
      </nav>
      <main className="wrap">
        {tab === 'Decision' ? <Decision /> : <div className="empty">Accuracy &mdash; coming in M5</div>}
      </main>
    </div>
  )
}
