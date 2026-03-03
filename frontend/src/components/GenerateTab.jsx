import { useState } from 'react'
import TemplateFlow from './TemplateFlow'
import CustomFlow from './CustomFlow'

export default function GenerateTab() {
  const [mode, setMode] = useState(null) // null | 'template' | 'custom'

  if (mode === 'template') {
    return <TemplateFlow onBack={() => setMode(null)} />
  }

  if (mode === 'custom') {
    return <CustomFlow onBack={() => setMode(null)} />
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

        <button
          onClick={() => setMode('custom')}
          className="w-52 h-36 rounded-xl border border-zinc-700 bg-zinc-900 hover:border-violet-500 hover:bg-zinc-800 transition-all text-left p-5 flex flex-col gap-2 group"
        >
          <span className="text-2xl">✏️</span>
          <span className="text-sm font-semibold text-zinc-100 group-hover:text-white">Custom Prompt</span>
          <span className="text-xs text-zinc-500">Write your own prompt</span>
        </button>
      </div>
    </div>
  )
}
