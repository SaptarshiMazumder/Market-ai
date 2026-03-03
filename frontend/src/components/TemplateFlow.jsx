import { useState, useEffect, useRef } from 'react'
import TemplateGrid from './TemplateGrid'
import { submitWithTemplate, pollGenerate } from '../services/api'

const DEFAULT_PARAMS = {
  width: 1024,
  height: 1024,
  steps: 15,
  cfg: 1.0,
  denoise: 1.0,
  lora_strength: 1.0,
  upscale_lora_strength: 0.6,
  seed: '',
}

export default function TemplateFlow({ onBack }) {
  const [selected, setSelected] = useState(null)
  const [subject, setSubject] = useState('')
  const [scenario, setScenario] = useState('')
  const [params, setParams] = useState(DEFAULT_PARAMS)
  const [genState, setGenState] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => () => clearInterval(pollRef.current), [])

  function handleSelect(template) {
    setSelected(template)
    setGenState(null)
  }

  function setParam(key, value) {
    setParams((p) => ({ ...p, [key]: value }))
  }

  async function handleGenerate() {
    if (!subject.trim()) return

    setGenState({ status: 'generating_prompt' })

    let jobId
    try {
      const res = await submitWithTemplate({
        subject: subject.trim(),
        scenario: scenario.trim() || undefined,
        lora_name: selected.lora_filename,
        keyword: selected.keyword,
        width: params.width,
        height: params.height,
        steps: params.steps,
        cfg: params.cfg,
        denoise: params.denoise,
        lora_strength: params.lora_strength,
        upscale_lora_strength: params.upscale_lora_strength,
        seed: params.seed === '' ? undefined : Number(params.seed),
      })
      jobId = res.job_id
      setGenState({
        status: 'processing',
        jobId,
        generated_prompt: res.generated_prompt,
      })
    } catch (e) {
      setGenState({ status: 'error', error: e.message })
      return
    }

    pollRef.current = setInterval(async () => {
      try {
        const job = await pollGenerate(jobId)
        if (job.status === 'completed') {
          clearInterval(pollRef.current)
          setGenState({
            status: 'completed',
            jobId,
            generated_prompt: job.generated_prompt,
            result: job.result,
          })
        } else if (job.status === 'failed') {
          clearInterval(pollRef.current)
          setGenState({
            status: 'error',
            error: job.error || 'Generation failed',
            generated_prompt: job.generated_prompt,
          })
        }
      } catch (e) {
        clearInterval(pollRef.current)
        setGenState({ status: 'error', error: e.message })
      }
    }, 4000)
  }

  const isRunning = ['generating_prompt', 'processing'].includes(genState?.status)
  const canGenerate = selected && subject.trim() && !isRunning

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={onBack}
          className="text-zinc-400 hover:text-zinc-200 text-sm transition-colors"
        >
          Back
        </button>
        <h2 className="text-base font-semibold text-zinc-200">Use Template</h2>
      </div>

      <div className="mb-8">
        <p className="text-xs text-zinc-500 uppercase tracking-wider mb-3 font-medium">
          Select a template
        </p>
        <TemplateGrid selected={selected} onSelect={handleSelect} />
      </div>

      {selected && (
        <div className="border-t border-zinc-800 pt-6 flex flex-col lg:flex-row gap-8">
          {/* Template preview */}
          <div className="w-full lg:w-72 shrink-0">
            <div className="aspect-square w-full max-w-xs rounded-xl overflow-hidden bg-zinc-800 mb-3">
              <img
                src={selected.preview_image_url}
                alt={selected.name}
                className="w-full h-full object-cover"
                onError={(e) => { e.target.style.display = 'none' }}
              />
            </div>
            <p className="text-sm font-semibold text-zinc-200">{selected.name}</p>
            {selected.keyword && (
              <p className="text-xs text-zinc-500 mt-0.5">
                Keyword: <span className="text-violet-400">{selected.keyword}</span>
              </p>
            )}
            <p className="text-xs text-zinc-600 mt-0.5">{selected.lora_filename}</p>
          </div>

          {/* Config */}
          <div className="flex-1 max-w-lg">
            <div className="mb-4">
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                Subject <span className="text-violet-400">*</span>
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. leather handbag, red sneakers, gold watch"
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
              />
            </div>

            <div className="mb-5">
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                Scenario <span className="text-zinc-600">(optional)</span>
              </label>
              <input
                type="text"
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                placeholder="e.g. walking through a night market, posing in a luxury hotel lobby"
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
              />
            </div>

            <div className="mb-5">
              <p className="text-xs font-medium text-zinc-400 mb-3">Parameters</p>
              <div className="grid grid-cols-2 gap-3">
                <ParamField label="Width" value={params.width} onChange={(v) => setParam('width', Number(v))} type="number" min={256} max={2048} step={64} />
                <ParamField label="Height" value={params.height} onChange={(v) => setParam('height', Number(v))} type="number" min={256} max={2048} step={64} />
                <ParamField label="Steps" value={params.steps} onChange={(v) => setParam('steps', Number(v))} type="number" min={1} max={50} />
                <ParamField label="CFG" value={params.cfg} onChange={(v) => setParam('cfg', Number(v))} type="number" min={0} max={20} step={0.1} />
                <ParamField label="LoRA Strength" value={params.lora_strength} onChange={(v) => setParam('lora_strength', Number(v))} type="number" min={0} max={2} step={0.05} />
                <ParamField label="Upscale LoRA" value={params.upscale_lora_strength} onChange={(v) => setParam('upscale_lora_strength', Number(v))} type="number" min={0} max={2} step={0.05} />
                <ParamField label="Seed" value={params.seed} onChange={(v) => setParam('seed', v)} type="number" placeholder="random" />
              </div>
            </div>

            <button
              onClick={handleGenerate}
              disabled={!canGenerate}
              className="w-full py-2.5 rounded-lg text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-violet-600 hover:bg-violet-500 text-white"
            >
              {genState?.status === 'generating_prompt' && 'Writing prompt...'}
              {genState?.status === 'processing' && 'Generating image...'}
              {(!genState || genState.status === 'completed' || genState.status === 'error') && 'Generate'}
            </button>

            {genState?.generated_prompt && (
              <div className="mt-3">
                <p className="text-xs text-zinc-500 mb-1">Generated prompt:</p>
                <p className="text-xs text-zinc-400 bg-zinc-900 rounded-lg p-3 leading-relaxed border border-zinc-800">
                  {genState.generated_prompt}
                </p>
              </div>
            )}

            {genState?.status === 'processing' && (
              <p className="mt-3 text-xs text-zinc-500 text-center animate-pulse">
                Running on RunPod — typically 60-120 seconds...
              </p>
            )}

            {genState?.status === 'error' && (
              <p className="mt-3 text-xs text-red-400 bg-red-950/30 rounded-lg p-3 border border-red-900/50">
                {genState.error}
              </p>
            )}

            {genState?.status === 'completed' && genState.result && (
              <div className="mt-5">
                <p className="text-xs text-zinc-500 mb-2">
                  Generated in {genState.result.duration_seconds}s
                  {genState.result.params?.seed != null && ` - seed ${genState.result.params.seed}`}
                </p>
                <div className="rounded-xl overflow-hidden border border-zinc-700">
                  <img src={genState.result.image_url} alt="Generated" className="w-full" />
                </div>
                <a
                  href={genState.result.image_url}
                  download
                  className="mt-2 inline-block text-xs text-violet-400 hover:text-violet-300"
                >
                  Download
                </a>
              </div>
            )}
          </div>
        </div>
      )}
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
