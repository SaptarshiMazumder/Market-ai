import { useState, useRef, useEffect } from 'react'
import { submitInpaint, pollInpaint, listMaskedImages, listProductImages } from '../services/api'

const DEFAULT_PARAMS = {
  prompt: 'product on a surface',
  steps: 4,
  denoise: 1.0,
  guidance: 4.0,
  seed: '',
}

export default function InpaintingTab() {
  const [maskHistory, setMaskHistory] = useState([])
  const [maskLoading, setMaskLoading] = useState(true)
  const [genHistory, setGenHistory] = useState([])
  const [genLoading, setGenLoading] = useState(true)

  const [selectedScene, setSelectedScene] = useState(null)
  const [manualScene, setManualScene] = useState('')

  const [selectedRef, setSelectedRef] = useState(null)
  const [manualRef, setManualRef] = useState('')

  const [params, setParams] = useState(DEFAULT_PARAMS)
  const [jobState, setJobState] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    listMaskedImages()
      .then((images) => {
        setMaskHistory(images)
        if (images.length > 0) setSelectedScene(images[0].r2_path)
      })
      .catch(() => {})
      .finally(() => setMaskLoading(false))

    listProductImages()
      .then((images) => {
        setGenHistory(images)
        if (images.length > 0) setSelectedRef(images[0].r2_path)
      })
      .catch(() => {})
      .finally(() => setGenLoading(false))
  }, [])

  useEffect(() => () => clearInterval(pollRef.current), [])

  function setParam(key, value) {
    setParams((p) => ({ ...p, [key]: value }))
  }

  const scene_url = manualScene.trim() || selectedScene || ''
  const reference_url = manualRef.trim() || selectedRef || ''

  async function handleSubmit() {
    if (!scene_url || !reference_url) return

    setJobState({ status: 'processing' })

    let jobId
    try {
      const res = await submitInpaint({
        scene_url,
        reference_url,
        prompt: params.prompt.trim() || 'product on a surface',
        steps: params.steps,
        denoise: params.denoise,
        guidance: params.guidance,
        seed: params.seed === '' ? undefined : Number(params.seed),
      })
      jobId = res.job_id
      setJobState({ status: 'processing', jobId })
    } catch (e) {
      setJobState({ status: 'error', error: e.message })
      return
    }

    pollRef.current = setInterval(async () => {
      try {
        const job = await pollInpaint(jobId)
        if (job.status === 'completed') {
          clearInterval(pollRef.current)
          setJobState({ status: 'completed', jobId, result: job.result })
        } else if (job.status === 'failed') {
          clearInterval(pollRef.current)
          setJobState({ status: 'error', error: job.error || 'Inpainting failed' })
        }
      } catch (e) {
        clearInterval(pollRef.current)
        setJobState({ status: 'error', error: e.message })
      }
    }, 4000)
  }

  const isRunning = jobState?.status === 'processing'
  const canSubmit = scene_url && reference_url && !isRunning

  return (
    <div>
      <h2 className="text-base font-semibold text-zinc-200 mb-1">Inpainting</h2>
      <p className="text-sm text-zinc-500 mb-6">
        Place a product into a masked scene using Flux 2 Klein.
      </p>

      <div className="flex flex-col lg:flex-row gap-8 max-w-5xl">
        {/* Left: inputs */}
        <div className="flex-1 max-w-md space-y-5">

          {/* Scene (masked image) */}
          <ImageSelector
            label="Scene image (masked)"
            description="The scene with the masked region where the product will be placed."
            history={maskHistory}
            loading={maskLoading}
            selected={selectedScene}
            onSelect={(r2) => { setSelectedScene(r2); setManualScene('') }}
            manual={manualScene}
            onManual={setManualScene}
            emptyMessage="No masked images in R2 yet — run Masking first."
          />

          {/* Reference (product image) */}
          <ImageSelector
            label="Reference image (product)"
            description="The product to place into the scene."
            history={genHistory}
            loading={genLoading}
            selected={selectedRef}
            onSelect={(r2) => { setSelectedRef(r2); setManualRef('') }}
            manual={manualRef}
            onManual={setManualRef}
            emptyMessage="No generated images yet — generate one first."
          />

          {/* Prompt */}
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">Prompt</label>
            <input
              type="text"
              value={params.prompt}
              onChange={(e) => setParam('prompt', e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
            />
          </div>

          {/* Params */}
          <div>
            <p className="text-xs font-medium text-zinc-400 mb-3">Parameters</p>
            <div className="grid grid-cols-2 gap-3">
              <ParamField label="Steps" value={params.steps} onChange={(v) => setParam('steps', Number(v))} type="number" min={1} max={20} />
              <ParamField label="Guidance" value={params.guidance} onChange={(v) => setParam('guidance', Number(v))} type="number" min={1} max={20} step={0.5} />
              <ParamField label="Denoise" value={params.denoise} onChange={(v) => setParam('denoise', Number(v))} type="number" min={0} max={1} step={0.05} />
              <ParamField label="Seed" value={params.seed} onChange={(v) => setParam('seed', v)} type="number" placeholder="random" />
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="w-full py-2.5 rounded-lg text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-violet-600 hover:bg-violet-500 text-white"
          >
            {isRunning ? 'Inpainting...' : 'Run Inpainting'}
          </button>

          {isRunning && (
            <p className="text-xs text-zinc-500 text-center animate-pulse">
              Running on RunPod — typically 30-90 seconds...
            </p>
          )}

          {jobState?.status === 'error' && (
            <p className="text-xs text-red-400 bg-red-950/30 rounded-lg p-3 border border-red-900/50">
              {jobState.error}
            </p>
          )}
        </div>

        {/* Right: result */}
        {jobState?.status === 'completed' && jobState.result && (
          <div className="flex-1">
            <p className="text-xs text-zinc-500 mb-2">
              Completed in {jobState.result.duration_seconds}s
              {jobState.result.params?.seed != null && ` — seed ${jobState.result.params.seed}`}
            </p>
            <div className="rounded-xl overflow-hidden border border-zinc-700">
              <img src={jobState.result.image_url} alt="Inpainted" className="w-full" />
            </div>
            {jobState.result.params && (
              <p className="mt-2 text-xs text-zinc-500">
                Steps: {jobState.result.params.steps} · Guidance: {jobState.result.params.guidance} · Denoise: {jobState.result.params.denoise}
              </p>
            )}
            <a
              href={jobState.result.image_url}
              download
              className="mt-2 inline-block text-xs text-violet-400 hover:text-violet-300"
            >
              Download
            </a>
          </div>
        )}
      </div>
    </div>
  )
}

function ImageSelector({ label, description, history, historyLabelKey, loading, selected, onSelect, manual, onManual, emptyMessage }) {
  return (
    <div>
      <p className="text-xs font-medium text-zinc-400 mb-1">
        {label} <span className="text-violet-400">*</span>
      </p>
      {description && <p className="text-xs text-zinc-600 mb-2">{description}</p>}

      {loading ? (
        <p className="text-xs text-zinc-600 mb-2 animate-pulse">Loading...</p>
      ) : history.length > 0 ? (
        <div className="flex flex-wrap gap-2 mb-2">
          {history.map((entry) => (
            <button
              key={entry.r2_path}
              onClick={() => onSelect(entry.r2_path)}
              title={historyLabelKey ? entry[historyLabelKey] : entry.r2_path}
              className={`w-14 h-14 rounded-lg overflow-hidden border-2 transition-all ${
                selected === entry.r2_path && !manual.trim()
                  ? 'border-violet-500'
                  : 'border-zinc-700 hover:border-zinc-500'
              }`}
            >
              <img
                src={entry.preview_url}
                alt={historyLabelKey ? entry[historyLabelKey] : ''}
                className="w-full h-full object-cover"
                onError={(e) => { e.target.style.opacity = '0.3' }}
              />
            </button>
          ))}
        </div>
      ) : (
        <p className="text-xs text-zinc-600 mb-2">{emptyMessage}</p>
      )}

      {selected && !manual.trim() && (
        <p className="text-xs text-zinc-600 mb-1 truncate">{selected}</p>
      )}

      <input
        type="text"
        value={manual}
        onChange={(e) => onManual(e.target.value)}
        placeholder="or enter r2://bucket/key manually"
        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
      />
    </div>
  )
}

function ParamField({ label, value, onChange, type, placeholder, ...rest }) {
  return (
    <div>
      <label className="block text-xs text-zinc-500 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
        {...rest}
      />
    </div>
  )
}
