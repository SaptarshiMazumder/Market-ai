import { useState } from 'react'
import GenerateTab from './components/GenerateTab'
import MaskingTab from './components/MaskingTab'
import InpaintingTab from './components/InpaintingTab'

export default function App() {
  const [tab, setTab] = useState('generate')

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-8 shrink-0">
        <span className="text-sm font-semibold text-white tracking-wide">Market AI</span>
        <nav className="flex gap-1">
          {[['generate', 'Generate'], ['masking', 'Masking'], ['inpainting', 'Inpainting']].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                tab === key ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main className="flex-1 p-6">
        {tab === 'generate' && <GenerateTab />}
        {tab === 'masking' && <MaskingTab />}
        {tab === 'inpainting' && <InpaintingTab />}
      </main>
    </div>
  )
}
