import { useState, useEffect, useRef } from 'react'
import {
  uploadProductImage,
  submitPipeline,
  listPipelines,
  getPipelineQueues,
} from '../services/api'
import QueueDashboard from './QueueDashboard'
import TemplateGrid from './TemplateGrid'

const POLL_INTERVAL = 5000

export default function PipelineTab() {
  const [queues, setQueues]           = useState(null)
  const [pipelines, setPipelines]     = useState([])
  const [mode, setMode]               = useState('no_template')
  const [subject, setSubject]         = useState('')
  const [productFile, setProductFile] = useState(null)
  const [productPreview, setProductPreview] = useState(null)
  const [productR2, setProductR2]     = useState(null)
  const [uploading, setUploading]     = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [runMasking, setRunMasking]       = useState(true)
  const [runInpainting, setRunInpainting] = useState(true)
  const [submitting, setSubmitting]       = useState(false)
  const [submitError, setSubmitError]     = useState(null)
  const pollRef = useRef(null)

  // ── Polling ──────────────────────────────────────────────────────────────
  async function refresh() {
    try {
      const [q, p] = await Promise.all([getPipelineQueues(), listPipelines()])
      setQueues(q)
      setPipelines(p)
    } catch (_) {}
  }

  useEffect(() => {
    refresh()
    pollRef.current = setInterval(refresh, POLL_INTERVAL)
    return () => clearInterval(pollRef.current)
  }, [])

  // ── Product image upload ──────────────────────────────────────────────────
  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setProductFile(file)
    setProductPreview(URL.createObjectURL(file))
    setProductR2(null)
    setUploading(true)
    try {
      const res = await uploadProductImage(file)
      setProductR2(res.r2_path)
    } catch (err) {
      setSubmitError(`Upload failed: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }

  // ── Submit ────────────────────────────────────────────────────────────────
  async function handleSubmit() {
    setSubmitError(null)
    if (!subject.trim())  return setSubmitError('Subject is required')
    if (!productR2)       return setSubmitError(uploading ? 'Image still uploading…' : 'Upload a product image first')
    if (mode === 'template' && !selectedTemplate) return setSubmitError('Select a template')

    setSubmitting(true)
    try {
      await submitPipeline({
        subject: subject.trim(),
        mode,
        product_r2: productR2,
        lora_name:         selectedTemplate?.lora_filename ?? null,
        keyword:           selectedTemplate?.keyword ?? null,
        template_name:     selectedTemplate?.name ?? null,
        preview_image_url: selectedTemplate?.preview_image_url ?? null,
        run_masking:    runMasking,
        run_inpainting: runInpainting,
      })
      await refresh()
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-5xl">
      <h2 className="text-base font-semibold text-zinc-200 mb-1">Pipeline</h2>
      <p className="text-sm text-zinc-500 mb-6">
        One click — image generation → masking → inpainting, fully automated.
      </p>

      <QueueDashboard queues={queues} />

      {/* ── Form ── */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5 mb-8 space-y-5 max-w-lg">

        {/* Product image upload */}
        <div>
          <p className="text-xs font-medium text-zinc-400 mb-2">
            Product image <span className="text-violet-400">*</span>
          </p>
          <label className="flex items-center gap-3 cursor-pointer group">
            <div className={`w-16 h-16 rounded-lg border-2 border-dashed flex items-center justify-center overflow-hidden shrink-0 transition-colors ${
              productPreview ? 'border-violet-500' : 'border-zinc-700 group-hover:border-zinc-500'
            }`}>
              {productPreview
                ? <img src={productPreview} className="w-full h-full object-cover" alt="product" />
                : <span className="text-zinc-600 text-xl">+</span>
              }
            </div>
            <div>
              <p className="text-sm text-zinc-300">
                {productFile ? productFile.name : 'Click to upload'}
              </p>
              <p className="text-xs text-zinc-600 mt-0.5">
                {uploading ? 'Uploading to R2…' : productR2 ? 'Uploaded ✓' : 'PNG, JPG, WEBP'}
              </p>
            </div>
            <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
          </label>
        </div>

        {/* Subject */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1.5">
            Subject <span className="text-violet-400">*</span>
          </label>
          <input
            type="text"
            value={subject}
            onChange={e => setSubject(e.target.value)}
            placeholder="e.g. jacket, sneakers, watch"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
          />
        </div>

        {/* Mode */}
        <div>
          <p className="text-xs font-medium text-zinc-400 mb-2">Mode</p>
          <div className="flex gap-4">
            {[['no_template', 'Custom Prompt'], ['template', 'Use Template']].map(([val, label]) => (
              <label key={val} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value={val}
                  checked={mode === val}
                  onChange={() => setMode(val)}
                  className="accent-violet-500"
                />
                <span className="text-sm text-zinc-300">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Template grid */}
        {mode === 'template' && (
          <div>
            <p className="text-xs font-medium text-zinc-400 mb-2">Select template</p>
            <TemplateGrid
              selected={selectedTemplate}
              onSelect={setSelectedTemplate}
            />
          </div>
        )}

        {/* Pipeline step toggles */}
        <div>
          <p className="text-xs font-medium text-zinc-400 mb-2">Run steps</p>
          <div className="flex flex-col gap-2">
            {[
              { label: 'Masking',    value: runMasking,    set: setRunMasking },
              { label: 'Inpainting', value: runInpainting, set: setRunInpainting,
                disabled: !runMasking },
            ].map(({ label, value, set, disabled }) => (
              <label key={label} className={`flex items-center gap-2.5 cursor-pointer select-none ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
                <button
                  type="button"
                  onClick={() => set(v => !v)}
                  className={`w-9 h-5 rounded-full transition-colors relative ${value ? 'bg-violet-600' : 'bg-zinc-700'}`}
                >
                  <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${value ? 'translate-x-4' : 'translate-x-0'}`} />
                </button>
                <span className="text-sm text-zinc-300">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {submitError && (
          <p className="text-xs text-red-400 bg-red-950/30 rounded-lg p-3 border border-red-900/50">
            {submitError}
          </p>
        )}

        <button
          onClick={handleSubmit}
          disabled={submitting || uploading}
          className="w-full py-2.5 rounded-lg text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-violet-600 hover:bg-violet-500 text-white"
        >
          {submitting ? 'Starting pipeline…' : 'Run Pipeline'}
        </button>
      </div>

      {/* ── Job list ── */}
      {pipelines.length > 0 && (
        <div className="space-y-4">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Pipeline Jobs</p>
          {pipelines.map(p => (
            <PipelineCard key={p.pipeline_id} pipeline={p} />
          ))}
        </div>
      )}
    </div>
  )
}

function PipelineCard({ pipeline: p }) {
  const statusColor = {
    running:   'text-yellow-400 bg-yellow-950/30 border-yellow-900/50',
    completed: 'text-green-400 bg-green-950/30 border-green-900/50',
    abandoned: 'text-red-400 bg-red-950/30 border-red-900/50',
  }[p.status] ?? 'text-zinc-400 bg-zinc-900 border-zinc-800'

  const nodeLabel = {
    image_gen:  'Image Gen',
    masking:    'Masking',
    inpainting: 'Inpainting',
    done:       'Done',
  }

  const steps = [
    { key: 'image_gen',  label: 'Image Gen',  result: p.image_gen_result },
    { key: 'masking',    label: 'Masking',     result: p.masking_result },
    { key: 'inpainting', label: 'Inpainting',  result: p.inpainting_result },
  ]

  const created = new Date(p.created_at * 1000).toLocaleTimeString()

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-sm font-medium text-zinc-200">{p.subject}</span>
          <span className="ml-2 text-xs text-zinc-600">{p.mode === 'template' ? 'Template' : 'Custom'} · {created}</span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${statusColor}`}>
          {p.status === 'running' ? `${nodeLabel[p.current_node] ?? p.current_node}…` : p.status}
        </span>
      </div>

      {/* Step timeline */}
      <div className="flex items-center gap-2 mb-3">
        {steps.map((step, i) => {
          const done = !!step.result
          const active = p.status === 'running' && p.current_node === step.key
          return (
            <div key={step.key} className="flex items-center gap-2">
              <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                done    ? 'bg-green-950/40 border-green-800 text-green-300' :
                active  ? 'bg-violet-950/40 border-violet-700 text-violet-300 animate-pulse' :
                          'bg-zinc-900 border-zinc-800 text-zinc-600'
              }`}>
                <span>{done ? '✓' : active ? '⏳' : '○'}</span>
                <span>{step.label}</span>
                {done && <span className="text-zinc-500">{step.result.score?.toFixed(1)}</span>}
              </div>
              {i < steps.length - 1 && (
                <span className="text-zinc-700">→</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Image gen agent checklist */}
      {p.agent_steps?.length > 0 && (
        <AgentChecklist steps={p.agent_steps} />
      )}

      {/* Image gen prompt */}
      {(p.current_prompt || p.image_gen_result?.prompt) && (
        <p className="text-xs text-zinc-500 italic mb-3 leading-relaxed">
          {p.current_prompt || p.image_gen_result.prompt}
        </p>
      )}

      {/* Masking agent checklist — shown once masking has started */}
      {p.masking_agent_steps?.length > 0 && p.image_gen_result && (
        <AgentChecklist steps={p.masking_agent_steps} />
      )}

      {/* Inpainting agent checklist — shown once inpainting has started */}
      {p.inpainting_agent_steps?.length > 0 && p.masking_result && (
        <AgentChecklist steps={p.inpainting_agent_steps} />
      )}

      {/* Inpainting prompt */}
      {(p.current_inpaint_prompt || p.inpainting_result?.prompt) && (
        <p className="text-xs text-zinc-500 italic mb-3 leading-relaxed">
          {p.current_inpaint_prompt || p.inpainting_result.prompt}
        </p>
      )}

      {/* Thumbnails */}
      {(p.image_gen_result || p.masking_result || p.inpainting_result) && (
        <div className="flex gap-2 mb-3">
          {steps.filter(s => s.result?.r2_path).map(step => (
            <ThumbnailFromR2 key={step.key} r2Path={step.result.r2_path} label={step.label} />
          ))}
        </div>
      )}

      {/* Abandon reason */}
      {p.status === 'abandoned' && p.error && (
        <p className="text-xs text-red-400 mt-2">{p.error}</p>
      )}

      {/* Final result */}
      {p.inpainting_result && (
        <FinalResult result={p.inpainting_result} />
      )}
    </div>
  )
}

function AgentChecklist({ steps }) {
  const icon = {
    pending:  { glyph: '○', cls: 'text-zinc-600' },
    running:  { glyph: '⏳', cls: 'text-violet-400 animate-pulse' },
    done:     { glyph: '✓', cls: 'text-green-400' },
    failed:   { glyph: '✗', cls: 'text-red-400' },
  }

  return (
    <div className="mb-3 pl-1 border-l-2 border-zinc-800 space-y-1">
      {steps.map(step => {
        const { glyph, cls } = icon[step.status] ?? icon.pending
        return (
          <div key={step.key} className="flex items-center gap-2">
            <span className={`text-xs font-mono w-4 text-center ${cls}`}>{glyph}</span>
            <span className={`text-xs ${step.status === 'running' ? 'text-zinc-200' : step.status === 'done' ? 'text-zinc-400' : step.status === 'failed' ? 'text-red-400' : 'text-zinc-600'}`}>
              {step.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function ThumbnailFromR2({ r2Path, label }) {
  const [url, setUrl] = useState(null)
  useEffect(() => {
    fetch(`/api/pipeline/preview?r2_path=${encodeURIComponent(r2Path)}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d?.preview_url && setUrl(d.preview_url))
      .catch(() => {})
  }, [r2Path])

  if (!url) return null
  return (
    <div className="w-14 h-14 rounded-lg overflow-hidden border border-zinc-700 shrink-0" title={label}>
      <img src={url} alt={label} className="w-full h-full object-cover" />
    </div>
  )
}

function FinalResult({ result }) {
  const [url, setUrl] = useState(null)
  useEffect(() => {
    fetch(`/api/pipeline/preview?r2_path=${encodeURIComponent(result.r2_path)}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d?.preview_url && setUrl(d.preview_url))
      .catch(() => {})
  }, [result.r2_path])

  return (
    <div className="mt-3 border-t border-zinc-800 pt-3">
      <p className="text-xs text-zinc-500 mb-2">
        Final result · score {result.score?.toFixed(1)} · {result.attempts_used} attempt{result.attempts_used > 1 ? 's' : ''}
      </p>
      {url && (
        <div className="rounded-xl overflow-hidden border border-zinc-700 max-w-sm">
          <img src={url} alt="Final result" className="w-full" />
        </div>
      )}
      {result.reason && <p className="text-xs text-zinc-600 mt-1 italic">{result.reason}</p>}
    </div>
  )
}
