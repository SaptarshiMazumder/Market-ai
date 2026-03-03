import { useState } from 'react'
import GenerateTab from './components/GenerateTab'

export default function App() {
  const [tab, setTab] = useState('generate')

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-8 shrink-0">
        <span className="text-sm font-semibold text-white tracking-wide">Market AI</span>
        <nav className="flex gap-1">
          <button
            onClick={() => setTab('generate')}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              tab === 'generate'
                ? 'bg-zinc-800 text-white'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Generate
          </button>
        </nav>
      </header>

      <main className="flex-1 p-6">
        {tab === 'generate' && <GenerateTab />}
      </main>
    </div>
  )
}
