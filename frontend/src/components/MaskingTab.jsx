import { useState, useRef, useEffect } from 'react'
import { submitMask, pollMask } from '../services/api'
import { loadImageHistory, saveMaskedImage } from '../lib/imageHistory'

const DEFAULT_PARAMS = {
  mask_blur: 50,
  mask_dilation: 50,
  seed: '',
}

export default function MaskingTab() {
  const [history, setHistory] = useState([])
  const [selectedR2, setSelectedR2] = useState(null)   // r2:// from history
  const [manualR2, setManualR2] = useState('')          // manual override
  const [objectName, setObjectName] = useState('')
  const [params, setParams] = useState(DEFAULT_PARAMS)
  const [jobState, setJobState] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    const h = loadImageHistory()
    setHistory(h)
    if (h.length > 0) setSelectedR2(h[0].r2_path)  // pre-select latest
  }, [])

  useEffect(() => () => clearInterval(pollRef.current), [])

  function setParam(key, value) {
    setParams((p) => ({ ...p, [key]: value }))
  }

  // Final image_url to use: manual override takes precedence
  const image_url = manualR2.trim() || selectedR2 || ''

  async function handleSubmit() {
    if (!image_url || !objectName.trim()) return

    setJobState({ status: 'processing' })

    let jobId
    try {
      const res = await submitMask({
        image_url,
        object_name: objectName.trim(),
        mask_blur: params.mask_blur,
        mask_dilation: params.mask_dilation,
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
        const job = await pollMask(jobId)
        if (job.status === 'completed') {
          clearInterval(pollRef.current)
          if (job.result?.r2_path) {
            saveMaskedImage({
              r2_path: job.result.r2_path,
              preview_url: job.result.image_url,
              object_name: objectName.trim(),
            })
          }
          setJobState({ status: 'completed', jobId, result: job.result })
        } else if (job.status === 'failed') {
          clearInterval(pollRef.current)
          setJobState({ status: 'error', error: job.error || 'Masking failed' })
        }
      } catch (e) {
        clearInterval(pollRef.current)
        setJobState({ status: 'error', error: e.message })
      }
    }, 4000)
  }

  const isRunning = jobState?.status === 'processing'
  const canSubmit = image_url && objectName.trim() && !isRunning

  return (
    <div>
      <h2 className="text-base font-semibold text-zinc-200 mb-1">Masking</h2>
      <p className="text-sm text-zinc-500 mb-6">
        Detect and mask an object in an image using Florence 2 + SAM2.
      </p>

      <div className="flex flex-col lg:flex-row gap-8 max-w-4xl">
        {/* Left: inputs */}
        <div className="flex-1 max-w-md">

          {/* Recent generated images */}
          <div className="mb-5">
            <p className="text-xs font-medium text-zinc-400 mb-2">
              Input image <span className="text-violet-400">*</span>
            </p>

            {history.length > 0 ? (
              <div className="flex flex-wrap gap-2 mb-3">
                {history.map((entry) => (
                  <button
                    key={entry.r2_path}
                    onClick={() => { setSelectedR2(entry.r2_path); setManualR2('') }}
                    title={entry.subject}
                    className={`w-16 h-16 rounded-lg overflow-hidden border-2 transition-all ${
                      selectedR2 === entry.r2_path && !manualR2.trim()
                        ? 'border-violet-500'
                        : 'border-zinc-700 hover:border-zinc-500'
                    }`}
                  >
                    <img
                      src={entry.preview_url}
                      alt={entry.subject}
                      className="w-full h-full object-cover"
                      onError={(e) => { e.target.style.opacity = '0.3' }}
                    />
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-zinc-600 mb-3">
                No generated images yet — generate one in the Generate tab first.
              </p>
            )}

            {/* Selected preview */}
            {(selectedR2 || manualR2.trim()) && !manualR2.trim() && (
              <p className="text-xs text-zinc-500 mb-2 truncate">
                Using: <span className="text-zinc-400">{selectedR2}</span>
              </p>
            )}

            {/* Manual override */}
            <input
              type="text"
              value={manualR2}
              onChange={(e) => setManualR2(e.target.value)}
              placeholder="or enter r2://bucket/key manually"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
            />
          </div>

          {/* Object name */}
          <div className="mb-5">
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              Object to mask <span className="text-violet-400">*</span>
            </label>
            <input
              type="text"
              value={objectName}
              onChange={(e) => setObjectName(e.target.value)}
              placeholder="e.g. headphone, shoe, bottle, watch"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
            />
          </div>

          {/* Params */}
          <div className="mb-5">
            <p className="text-xs font-medium text-zinc-400 mb-3">Parameters</p>
            <div className="space-y-3">
              <SliderField
                label={`Mask Blur (${params.mask_blur})`}
                value={params.mask_blur}
                onChange={(v) => setParam('mask_blur', Number(v))}
                min={0} max={100}
              />
              <SliderField
                label={`Mask Dilation (${params.mask_dilation})`}
                value={params.mask_dilation}
                onChange={(v) => setParam('mask_dilation', Number(v))}
                min={0} max={100}
              />
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Seed</label>
                <input
                  type="number"
                  value={params.seed}
                  onChange={(e) => setParam('seed', e.target.value)}
                  placeholder="random"
                  className="w-40 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
                />
              </div>
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="w-full py-2.5 rounded-lg text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-violet-600 hover:bg-violet-500 text-white"
          >
            {isRunning ? 'Masking...' : 'Generate Mask'}
          </button>

          {isRunning && (
            <p className="mt-3 text-xs text-zinc-500 text-center animate-pulse">
              Running on RunPod — typically 20-60 seconds...
            </p>
          )}

          {jobState?.status === 'error' && (
            <p className="mt-3 text-xs text-red-400 bg-red-950/30 rounded-lg p-3 border border-red-900/50">
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
              <img src={jobState.result.image_url} alt="Masked" className="w-full" />
            </div>
            {jobState.result.params && (
              <p className="mt-2 text-xs text-zinc-500">
                Blur: {jobState.result.params.mask_blur} · Dilation: {jobState.result.params.mask_dilation}
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

function SliderField({ label, value, onChange, min, max }) {
  return (
    <div>
      <label className="block text-xs text-zinc-500 mb-1">{label}</label>
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        min={min}
        max={max}
        className="w-full accent-violet-500"
      />
    </div>
  )
}
