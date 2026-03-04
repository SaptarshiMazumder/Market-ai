const SERVICES = [
  { key: 'lora_z_turbo', label: 'LoRA Z-Turbo' },
  { key: 'z_turbo',      label: 'Z-Turbo' },
  { key: 'masking',      label: 'Masking' },
  { key: 'inpainting',   label: 'Inpainting' },
]

export default function QueueDashboard({ queues }) {
  return (
    <div className="grid grid-cols-4 gap-3 mb-8">
      {SERVICES.map(({ key, label }) => {
        const count = queues?.[key] ?? 0
        return (
          <div
            key={key}
            className={`rounded-xl border px-4 py-3 text-center transition-colors ${
              count > 0
                ? 'border-violet-600 bg-violet-950/40'
                : 'border-zinc-800 bg-zinc-900/50'
            }`}
          >
            <p className="text-xs text-zinc-500 mb-1">{label}</p>
            <p className={`text-2xl font-bold tabular-nums ${count > 0 ? 'text-violet-300' : 'text-zinc-600'}`}>
              {count}
            </p>
            <p className="text-xs text-zinc-600 mt-0.5">active</p>
          </div>
        )
      })}
    </div>
  )
}
