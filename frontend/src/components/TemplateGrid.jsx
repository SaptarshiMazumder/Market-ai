import { useEffect, useState } from 'react'
import { listTemplates } from '../services/api'

export default function TemplateGrid({ selected, onSelect }) {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    listTemplates()
      .then(setTemplates)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const filtered = templates.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) {
    return <p className="text-sm text-zinc-500">Loading templates...</p>
  }

  if (error) {
    return <p className="text-sm text-red-400">Error: {error}</p>
  }

  if (templates.length === 0) {
    return <p className="text-sm text-zinc-500">No templates found. Create one first.</p>
  }

  return (
    <div>
      <input
        type="text"
        placeholder="Search templates..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-4 w-full max-w-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-violet-500"
      />

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {filtered.map((t) => {
          const isSelected = selected?.id === t.id
          return (
            <button
              key={t.id}
              onClick={() => onSelect(t)}
              className={`rounded-xl overflow-hidden border-2 transition-all text-left ${
                isSelected
                  ? 'border-violet-500 ring-1 ring-violet-500/30'
                  : 'border-zinc-700 hover:border-zinc-500'
              }`}
            >
              <div className="aspect-square bg-zinc-800 overflow-hidden">
                <img
                  src={t.image_url}
                  alt={t.name}
                  className="w-full h-full object-cover"
                  onError={(e) => { e.target.style.display = 'none' }}
                />
              </div>
              <div className="px-2 py-1.5 bg-zinc-900">
                <p className="text-xs font-medium text-zinc-200 truncate">{t.name}</p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
