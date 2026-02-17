import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  // Model selection
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState(null)
  const [modelsLoading, setModelsLoading] = useState(true)
  const [modelsError, setModelsError] = useState(null)

  // Generation form
  const [prompt, setPrompt] = useState('')
  const [refImage, setRefImage] = useState(null)
  const [refPreview, setRefPreview] = useState(null)
  const [loraScale, setLoraScale] = useState(1.0)
  const [promptStrength, setPromptStrength] = useState(0.8)
  const [guidanceScale, setGuidanceScale] = useState(3.5)
  const [numSteps, setNumSteps] = useState(28)

  // Generation state
  const [generating, setGenerating] = useState(false)
  const [generatedImage, setGeneratedImage] = useState(null)
  const [genError, setGenError] = useState(null)

  const formatDuration = (seconds) => {
    if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return '-'
    if (seconds < 1) return '<1s'
    const total = Math.floor(seconds)
    if (total >= 3600) {
      const h = Math.floor(total / 3600)
      const m = Math.floor((total % 3600) / 60)
      return `${h}h ${m}m`
    }
    if (total >= 60) {
      const m = Math.floor(total / 60)
      const s = total % 60
      return `${m}m ${s}s`
    }
    return `${total}s`
  }

  const formatRelativeTime = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    if (Number.isNaN(date.getTime())) return '-'
    const diffMs = Date.now() - date.getTime()
    const diffSec = Math.floor(diffMs / 1000)
    if (diffSec < 0) return 'just now'
    if (diffSec < 60) return `${diffSec}s ago`
    const diffMin = Math.floor(diffSec / 60)
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHr = Math.floor(diffMin / 60)
    if (diffHr < 24) return `${diffHr}h ago`
    const diffDay = Math.floor(diffHr / 24)
    return `${diffDay}d ago`
  }

  useEffect(() => {
    axios.get('/api/models')
      .then(res => {
        setModels(res.data.models)
        setModelsLoading(false)
      })
      .catch(err => {
        setModelsError(err.response?.data?.error || err.message)
        setModelsLoading(false)
      })
  }, [])

  const succeededModels = models.filter(m => m.status === 'succeeded' && m.model_string)
  const otherModels = models.filter(m => m.status !== 'succeeded' || !m.model_string)

  function handleImageChange(e) {
    const file = e.target.files[0]
    if (file) {
      setRefImage(file)
      setRefPreview(URL.createObjectURL(file))
    }
  }

  function clearImage() {
    setRefImage(null)
    setRefPreview(null)
  }

  async function handleGenerate(e) {
    e.preventDefault()
    if (!selectedModel || !prompt.trim()) return

    setGenerating(true)
    setGenError(null)
    setGeneratedImage(null)

    try {
      const formData = new FormData()
      formData.append('model_string', selectedModel.model_string)
      formData.append('prompt', prompt)
      formData.append('lora_scale', loraScale)
      formData.append('prompt_strength', promptStrength)
      formData.append('guidance_scale', guidanceScale)
      formData.append('num_inference_steps', numSteps)
      if (refImage) {
        formData.append('image', refImage)
      }

      const res = await axios.post('/api/generate', formData)
      setGeneratedImage(res.data.image_url)
    } catch (err) {
      setGenError(err.response?.data?.error || err.message)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-5">
        <h1 className="text-2xl font-bold">Market AI</h1>
        <p className="text-sm text-gray-400 mt-1">Generate images with your trained Flux LoRA models</p>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        {/* Model Selection */}
        <section>
          <h2 className="text-lg font-semibold mb-4 text-gray-300">1. Select a Model</h2>

          {modelsLoading && (
            <div className="text-center py-10">
              <div className="inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-gray-400 text-sm">Fetching models...</p>
            </div>
          )}

          {modelsError && (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
              {modelsError}
            </div>
          )}

          {!modelsLoading && !modelsError && (
            <div className="space-y-2">
              {succeededModels.map((model, i) => {
                const isSelected = selectedModel?.model_string === model.model_string
                return (
                  <button
                    key={i}
                    onClick={() => setSelectedModel(model)}
                    className={`w-full text-left p-4 rounded-lg border transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-gray-800 bg-gray-900 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{model.destination}</p>
                        <p className="text-xs text-gray-500 mt-1 font-mono">{model.model_string}</p>
                        <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-500">
                          <div>
                            <span className="text-gray-600">ID</span>
                            <div className="font-mono break-all text-gray-400">{model.id || '-'}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Model</span>
                            <div className="font-mono break-all text-gray-400">{model.model || '-'}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Source</span>
                            <div className="text-gray-400">{model.source || '-'}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Queued</span>
                            <div className="text-gray-400">{formatDuration(model.queued_seconds)}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Running</span>
                            <div className="text-gray-400">{formatDuration(model.running_seconds)}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Total</span>
                            <div className="text-gray-400">{formatDuration(model.total_seconds)}</div>
                          </div>
                          <div>
                            <span className="text-gray-600">Created</span>
                            <div className="text-gray-400" title={model.created_at || ''}>
                              {formatRelativeTime(model.created_at)}
                            </div>
                          </div>
                        </div>
                      </div>
                      <span className="text-xs px-2 py-1 rounded-full bg-green-900/50 text-green-400 border border-green-800">
                        ready
                      </span>
                    </div>
                  </button>
                )
              })}

              {otherModels.map((model, i) => (
                <div key={`other-${i}`} className="p-4 rounded-lg border border-gray-800 bg-gray-900 opacity-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{model.destination}</p>
                      <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-500">
                        <div>
                          <span className="text-gray-600">ID</span>
                          <div className="font-mono break-all text-gray-400">{model.id || '-'}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Model</span>
                          <div className="font-mono break-all text-gray-400">{model.model || '-'}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Source</span>
                          <div className="text-gray-400">{model.source || '-'}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Queued</span>
                          <div className="text-gray-400">{formatDuration(model.queued_seconds)}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Running</span>
                          <div className="text-gray-400">{formatDuration(model.running_seconds)}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Total</span>
                          <div className="text-gray-400">{formatDuration(model.total_seconds)}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Created</span>
                          <div className="text-gray-400" title={model.created_at || ''}>
                            {formatRelativeTime(model.created_at)}
                          </div>
                        </div>
                      </div>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full border ${
                      model.status === 'processing'
                        ? 'bg-yellow-900/50 text-yellow-400 border-yellow-800'
                        : 'bg-red-900/50 text-red-400 border-red-800'
                    }`}>
                      {model.status}
                    </span>
                  </div>
                </div>
              ))}

              {succeededModels.length === 0 && otherModels.length === 0 && (
                <p className="text-gray-500 text-center py-10">No models found.</p>
              )}
            </div>
          )}
        </section>

        {/* Generation Form - only show when model is selected */}
        {selectedModel && (
          <section className="mt-10">
            <h2 className="text-lg font-semibold mb-4 text-gray-300">2. Generate Image</h2>

            <form onSubmit={handleGenerate} className="space-y-6">
              {/* Prompt */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Prompt</label>
                <textarea
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder="Describe the image you want to generate..."
                  rows={3}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              {/* Reference Image */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Reference Image <span className="text-gray-600">(optional)</span>
                </label>
                {refPreview ? (
                  <div className="flex items-start gap-4">
                    <img src={refPreview} alt="Reference" className="w-32 h-32 object-cover rounded-lg border border-gray-700" />
                    <button
                      type="button"
                      onClick={clearImage}
                      className="text-sm text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <label className="flex items-center justify-center w-full h-32 border-2 border-dashed border-gray-700 rounded-lg cursor-pointer hover:border-gray-500 transition-colors">
                    <div className="text-center">
                      <p className="text-gray-500 text-sm">Click to upload</p>
                      <p className="text-gray-600 text-xs mt-1">PNG, JPG, WEBP</p>
                    </div>
                    <input type="file" accept="image/*" onChange={handleImageChange} className="hidden" />
                  </label>
                )}
              </div>

              {/* Parameters */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    LoRA Scale <span className="text-gray-600 font-mono text-xs ml-1">{loraScale}</span>
                  </label>
                  <input
                    type="range" min="0" max="1.5" step="0.05"
                    value={loraScale}
                    onChange={e => setLoraScale(parseFloat(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                  <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>0</span><span>1.5</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Prompt Strength <span className="text-gray-600 font-mono text-xs ml-1">{promptStrength}</span>
                  </label>
                  <input
                    type="range" min="0" max="1" step="0.05"
                    value={promptStrength}
                    onChange={e => setPromptStrength(parseFloat(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                  <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>0 (keep image)</span><span>1 (follow prompt)</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Guidance Scale <span className="text-gray-600 font-mono text-xs ml-1">{guidanceScale}</span>
                  </label>
                  <input
                    type="range" min="1" max="10" step="0.5"
                    value={guidanceScale}
                    onChange={e => setGuidanceScale(parseFloat(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                  <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>1</span><span>10</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Inference Steps <span className="text-gray-600 font-mono text-xs ml-1">{numSteps}</span>
                  </label>
                  <input
                    type="range" min="10" max="50" step="1"
                    value={numSteps}
                    onChange={e => setNumSteps(parseInt(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                  <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>10 (fast)</span><span>50 (quality)</span>
                  </div>
                </div>
              </div>

              {/* Generate Button */}
              <button
                type="submit"
                disabled={generating || !prompt.trim()}
                className="w-full py-3 px-6 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-500 text-white"
              >
                {generating ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Generating...
                  </span>
                ) : (
                  'Generate Image'
                )}
              </button>
            </form>

            {/* Error */}
            {genError && (
              <div className="mt-6 bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
                {genError}
              </div>
            )}

            {/* Result */}
            {generatedImage && (
              <div className="mt-8">
                <h3 className="text-lg font-semibold text-gray-300 mb-4">Result</h3>
                <img
                  src={generatedImage}
                  alt="Generated"
                  className="w-full rounded-lg border border-gray-800"
                />
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

export default App
