import { useState } from 'react'
import Decision from './pages/Decision'
import Accuracy from './pages/Accuracy'
import { BarChart3, Wind } from 'lucide-react'

type Tab = 'Decision' | 'Accuracy'

export default function App() {
  const [tab, setTab] = useState<Tab>('Decision')
  const [accuracySelectedDay, setAccuracySelectedDay] = useState<string | null>(null)
  return (
    <div className="app">
      <div className="bg-orbs" aria-hidden="true">
        <div className="orb orb-cyan" />
        <div className="orb orb-violet" />
        <div className="orb orb-blue" />
      </div>
      <nav className="tabs" aria-label="Section">
        <button
          className={`tab ${tab === 'Decision' ? 'active' : ''}`}
          onClick={() => setTab('Decision')}
        >
          <Wind size={16} strokeWidth={1.75} /> Decision
        </button>
        <button
          className={`tab ${tab === 'Accuracy' ? 'active' : ''}`}
          onClick={() => setTab('Accuracy')}
        >
          <BarChart3 size={16} strokeWidth={1.75} /> Accuracy
        </button>
      </nav>
      <main className="wrap">
        {tab === 'Decision' ? <Decision initialDay={accuracySelectedDay ?? undefined} /> : <Accuracy onSelectDay={(d) => { setAccuracySelectedDay(d); setTab('Decision') }} />}
      </main>
    </div>
  )
}
