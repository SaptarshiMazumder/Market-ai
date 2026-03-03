import { useState } from 'react'
import TemplateFlow from './TemplateFlow'

export default function GenerateTab() {
  const [mode, setMode] = useState(null) // null | 'template' | 'custom'

  if (mode === 'template') {
    return <TemplateFlow onBack={() => setMode(null)} />
  }

  return (
    <div>
      <h2 className="text-base font-semibold text-zinc-200 mb-1">Generate Images</h2>
      <p className="text-sm text-zinc-500 mb-6">Choose how you want to start.</p>

      <div className="flex gap-4">
        <button
          onClick={() => setMode('template')}
          className="w-52 h-36 rounded-xl border border-zinc-700 bg-zinc-900 hover:border-violet-500 hover:bg-zinc-800 transition-all text-left p-5 flex flex-col gap-2 group"
        >
          <span className="text-2xl">🖼️</span>
          <span className="text-sm font-semibold text-zinc-100 group-hover:text-white">Use Template</span>
          <span className="text-xs text-zinc-500">Pick a preset prompt and image style</span>
        </button>

        <div className="w-52 h-36 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 flex flex-col gap-2 opacity-40 cursor-not-allowed">
          <span className="text-2xl">✏️</span>
          <span className="text-sm font-semibold text-zinc-400">Custom Prompt</span>
          <span className="text-xs text-zinc-600">Write your own prompt</span>
        </div>
      </div>
    </div>
  )
}
