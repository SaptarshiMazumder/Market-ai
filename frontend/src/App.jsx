import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

function App() {
  // Step 1 mode
  const [step1Mode, setStep1Mode] = useState('existing') // 'existing' | 'train'

  // Model selection
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState(null)
  const [modelsLoading, setModelsLoading] = useState(true)
  const [modelsError, setModelsError] = useState(null)

  // Training form
  const [trainModelName, setTrainModelName] = useState('')
  const [trainTriggerWord, setTrainTriggerWord] = useState('TOK')
  const [trainZip, setTrainZip] = useState(null)
  const [trainZipName, setTrainZipName] = useState('')
  const [trainConfig, setTrainConfig] = useState(null)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Training state
  const [trainingId, setTrainingId] = useState(null)
  const [trainingStatus, setTrainingStatus] = useState(null)
  const [trainingLogs, setTrainingLogs] = useState('')
  const [trainingError, setTrainingError] = useState(null)
  const [startingTraining, setStartingTraining] = useState(false)
  const pollRef = useRef(null)

  // Templates
  const [templates, setTemplates] = useState([])
  const [templatesLoading, setTemplatesLoading] = useState(true)
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [showAddTemplate, setShowAddTemplate] = useState(false)
  const [newTemplateName, setNewTemplateName] = useState('')
  const [newTemplatePrompt, setNewTemplatePrompt] = useState('')
  const [newTemplateImage, setNewTemplateImage] = useState(null)
  const [newTemplateImagePreview, setNewTemplateImagePreview] = useState(null)
  const [savingTemplate, setSavingTemplate] = useState(false)

  // Generation form
  const [prompt, setPrompt] = useState('')
  const [refImage, setRefImage] = useState(null)
  const [refPreview, setRefPreview] = useState(null)
  const [loraScale, setLoraScale] = useState(1.1)
  const [promptStrength, setPromptStrength] = useState(0.8)
  const [guidanceScale, setGuidanceScale] = useState(3)
  const [numSteps, setNumSteps] = useState(28)

  // Generation state
  const [generating, setGenerating] = useState(false)
  const [generatedImage, setGeneratedImage] = useState(null)
  const [genError, setGenError] = useState(null)

  // Upscale state
  const [upscaling, setUpscaling] = useState(false)
  const [upscaledImage, setUpscaledImage] = useState(null)
  const [upscalePrompt, setUpscalePrompt] = useState(null)
  const [upscaleNegPrompt, setUpscaleNegPrompt] = useState(null)
  const [upscaleError, setUpscaleError] = useState(null)

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

  // Fetch training config defaults
  useEffect(() => {
    axios.get('/api/training-config')
      .then(res => setTrainConfig(res.data))
      .catch(() => {})
  }, [])

  // Fetch existing models — resume polling if any are still training
  useEffect(() => {
    axios.get('/api/models')
      .then(res => {
        const allModels = res.data.models
        setModels(allModels)
        setModelsLoading(false)

        // Resume polling for the most recent in-progress job
        const inProgress = allModels.find(m => m.status === 'training' && m.runpod_job_id)
        if (inProgress && !trainingId) {
          console.log('[Resume] Resuming poll for job', inProgress.runpod_job_id)
          setTrainingId(inProgress.runpod_job_id)
          setTrainingStatus('training')
          setStep1Mode('train')
        }
      })
      .catch(err => {
        setModelsError(err.response?.data?.error || err.message)
        setModelsLoading(false)
      })
  }, [])

  // Fetch templates
  useEffect(() => {
    axios.get('/api/templates')
      .then(res => {
        setTemplates(res.data.templates)
        setTemplatesLoading(false)
      })
      .catch(() => setTemplatesLoading(false))
  }, [])

  // Poll training status
  useEffect(() => {
    if (!trainingId) return

    function poll() {
      axios.get(`/api/training-status/${trainingId}`)
        .then(res => {
          const { status, logs, model_string, trigger_word, model_name, error } = res.data
          setTrainingStatus(status)
          if (logs) setTrainingLogs(logs)

          if (status === 'succeeded' && model_string) {
            setSelectedModel({
              model_string: model_string,
              destination: model_name || trainModelName,
              trigger_word: trigger_word || trainTriggerWord,
            })
            setTrainingId(null)
            setStep1Mode('existing')
            axios.get('/api/models').then(r => setModels(r.data.models))
          } else if (status === 'failed' || status === 'canceled') {
            setTrainingError(error || `Training ${status}`)
            setTrainingId(null)
          }
        })
        .catch(err => {
          setTrainingError(err.response?.data?.error || err.message)
          setTrainingId(null)
        })
    }

    poll()
    pollRef.current = setInterval(poll, 5000)
    return () => clearInterval(pollRef.current)
  }, [trainingId])

  // When a template is selected, inject prompt with trigger word replaced
  useEffect(() => {
    if (!selectedTemplate) return
    const triggerWord = selectedModel?.trigger_word || 'TOK'
    const resolved = selectedTemplate.prompt.replace(/trigger_keyword/gi, triggerWord)
    setPrompt(resolved)
  }, [selectedTemplate, selectedModel])

  const succeededModels = models.filter(m => m.status === 'succeeded' && m.model_string)
  const otherModels = models.filter(m => m.status !== 'succeeded' || !m.model_string)

  function handleZipChange(e) {
    const file = e.target.files[0]
    if (file) {
      setTrainZip(file)
      setTrainZipName(file.name)
    }
  }

  async function handleStartTraining(e) {
    e.preventDefault()
    if (!trainModelName.trim() || !trainZip) return

    setStartingTraining(true)
    setTrainingError(null)
    setTrainingStatus(null)
    setTrainingLogs('')

    try {
      const formData = new FormData()
      formData.append('model_name', trainModelName.trim().toLowerCase().replace(/\s+/g, '_'))
      formData.append('trigger_word', trainTriggerWord.trim() || 'TOK')
      formData.append('images', trainZip)
      if (trainConfig) {
        formData.append('steps', trainConfig.steps)
        formData.append('lr', trainConfig.lr)
        formData.append('lora_rank', trainConfig.lora_rank)
        formData.append('batch_size', trainConfig.batch_size)
        formData.append('resolution', JSON.stringify(trainConfig.resolution))
      }

      const res = await axios.post('/api/train', formData)
      setTrainingId(res.data.job_id)
      setTrainingStatus('starting')
    } catch (err) {
      setTrainingError(err.response?.data?.error || err.message)
    } finally {
      setStartingTraining(false)
    }
  }

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
    autoGenerate(prompt)
  }

  async function autoGenerate(promptText) {
    if (!selectedModel || !promptText.trim()) return

    setGenerating(true)
    setGenError(null)
    setGeneratedImage(null)
    setUpscaledImage(null)
    setUpscalePrompt(null)
    setUpscaleNegPrompt(null)
    setUpscaleError(null)

    try {
      const formData = new FormData()
      formData.append('model_id', selectedModel.id)
      formData.append('prompt', promptText)
      formData.append('lora_scale', loraScale)
      formData.append('prompt_strength', promptStrength)
      formData.append('guidance_scale', guidanceScale)
      formData.append('num_inference_steps', numSteps)
      if (refImage) {
        formData.append('image', refImage)
      }

      const res = await axios.post('/api/generate', formData)
      setGeneratedImage(res.data.image_url)
      autoUpscale(res.data.image_url)
    } catch (err) {
      setGenError(err.response?.data?.error || err.message)
      setGenerating(false)
    }
  }

  async function autoUpscale(imageUrl) {
    setGenerating(false)

    const filename = imageUrl.split('/').pop()

    setUpscaling(true)
    setUpscaleError(null)
    setUpscaledImage(null)

    try {
      const res = await axios.post('/api/upscale', { image_filename: filename })
      setUpscaledImage(res.data.image_url)
      setUpscalePrompt(res.data.prompt)
      setUpscaleNegPrompt(res.data.negative_prompt)
    } catch (err) {
      setUpscaleError(err.response?.data?.error || err.message)
    } finally {
      setUpscaling(false)
    }
  }

  async function handleUpscale() {
    if (!generatedImage) return
    autoUpscale(generatedImage)
  }

  // Template management
  function handleNewTemplateImageChange(e) {
    const file = e.target.files[0]
    if (file) {
      setNewTemplateImage(file)
      setNewTemplateImagePreview(URL.createObjectURL(file))
    }
  }

  async function handleSaveTemplate(e) {
    e.preventDefault()
    if (!newTemplateName.trim() || !newTemplatePrompt.trim() || !newTemplateImage) return

    setSavingTemplate(true)
    try {
      const formData = new FormData()
      formData.append('name', newTemplateName.trim())
      formData.append('prompt', newTemplatePrompt.trim())
      formData.append('image', newTemplateImage)

      const res = await axios.post('/api/templates', formData)
      setTemplates(prev => [res.data, ...prev])
      setNewTemplateName('')
      setNewTemplatePrompt('')
      setNewTemplateImage(null)
      setNewTemplateImagePreview(null)
      setShowAddTemplate(false)
    } catch (err) {
      alert(err.response?.data?.error || err.message)
    } finally {
      setSavingTemplate(false)
    }
  }

  async function handleDeleteTemplate(templateId) {
    try {
      await axios.delete(`/api/templates/${templateId}`)
      setTemplates(prev => prev.filter(t => t.id !== templateId))
      if (selectedTemplate?.id === templateId) {
        setSelectedTemplate(null)
        setPrompt('')
      }
    } catch (err) {
      alert(err.response?.data?.error || err.message)
    }
  }

  const isTraining = !!trainingId

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-5">
        <h1 className="text-2xl font-bold">Market AI</h1>
        <p className="text-sm text-gray-400 mt-1">Generate images with your trained Flux LoRA models</p>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        {/* Step 1 */}
        <section>
          <h2 className="text-lg font-semibold mb-4 text-gray-300">1. Choose a Model</h2>

          <div className="flex gap-1 mb-6 bg-gray-900 p-1 rounded-lg w-fit">
            <button
              onClick={() => setStep1Mode('existing')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                step1Mode === 'existing'
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-gray-300'
              }`}
            >
              Use Existing
            </button>
            <button
              onClick={() => setStep1Mode('train')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                step1Mode === 'train'
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-gray-300'
              }`}
            >
              Train New
            </button>
          </div>

          {step1Mode === 'existing' && (
            <>
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
                            {model.trigger_word && (
                              <p className="text-xs text-blue-400 mt-1">Trigger: <span className="font-mono">{model.trigger_word}</span></p>
                            )}
                            <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-500">
                              <div>
                                <span className="text-gray-600">ID</span>
                                <div className="font-mono break-all text-gray-400">{model.id || '-'}</div>
                              </div>
                              <div>
                                <span className="text-gray-600">Source</span>
                                <div className="text-gray-400">{model.source || '-'}</div>
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
                              <span className="text-gray-600">Status</span>
                              <div className="text-gray-400">{model.status}</div>
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
                            : model.status === 'training'
                            ? 'bg-orange-900/50 text-orange-400 border-orange-800'
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
            </>
          )}

          {step1Mode === 'train' && (
            <>
              {!isTraining && !trainingError && (
                <form onSubmit={handleStartTraining} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">Model Name</label>
                    <input
                      type="text"
                      value={trainModelName}
                      onChange={e => setTrainModelName(e.target.value)}
                      placeholder="e.g. my_product"
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-600 mt-1">Used as the LoRA filename in R2</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">Trigger Word</label>
                    <input
                      type="text"
                      value={trainTriggerWord}
                      onChange={e => setTrainTriggerWord(e.target.value)}
                      placeholder="TOK"
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-600 mt-1">Use this word in prompts to activate the trained style</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">Training Images (.zip)</label>
                    <label className="flex items-center justify-center w-full h-32 border-2 border-dashed border-gray-700 rounded-lg cursor-pointer hover:border-gray-500 transition-colors">
                      <div className="text-center">
                        {trainZipName ? (
                          <p className="text-gray-300 text-sm">{trainZipName}</p>
                        ) : (
                          <>
                            <p className="text-gray-500 text-sm">Click to upload .zip</p>
                            <p className="text-gray-600 text-xs mt-1">ZIP file containing training images</p>
                          </>
                        )}
                      </div>
                      <input type="file" accept=".zip" onChange={handleZipChange} className="hidden" />
                    </label>
                  </div>

                  {trainConfig && (
                    <div>
                      <button
                        type="button"
                        onClick={() => setShowAdvanced(v => !v)}
                        className="text-sm text-gray-400 hover:text-gray-300 flex items-center gap-1"
                      >
                        {showAdvanced ? '▾' : '▸'} Advanced Settings
                      </button>
                      {showAdvanced && (
                        <div className="mt-3 grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Steps</label>
                            <input type="number" value={trainConfig.steps}
                              onChange={e => setTrainConfig(c => ({ ...c, steps: parseInt(e.target.value) }))}
                              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Learning Rate</label>
                            <input type="number" step="0.00001" value={trainConfig.lr}
                              onChange={e => setTrainConfig(c => ({ ...c, lr: parseFloat(e.target.value) }))}
                              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">LoRA Rank</label>
                            <input type="number" value={trainConfig.lora_rank}
                              onChange={e => setTrainConfig(c => ({ ...c, lora_rank: parseInt(e.target.value) }))}
                              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Batch Size</label>
                            <input type="number" value={trainConfig.batch_size}
                              onChange={e => setTrainConfig(c => ({ ...c, batch_size: parseInt(e.target.value) }))}
                              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={startingTraining || !trainModelName.trim() || !trainZip}
                    className="w-full py-3 px-6 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-purple-600 hover:bg-purple-500 text-white"
                  >
                    {startingTraining ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Starting Training...
                      </span>
                    ) : (
                      'Start Training'
                    )}
                  </button>
                </form>
              )}

              {isTraining && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 rounded-lg border border-purple-800 bg-purple-900/20">
                    <span className="w-5 h-5 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
                    <div>
                      <p className="font-medium text-purple-300">Training in progress</p>
                      <p className="text-xs text-gray-400 mt-1">
                        Status: <span className="text-purple-300">{trainingStatus}</span>
                        {' — '}polling every 5s
                      </p>
                    </div>
                  </div>

                  {trainingLogs && (
                    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                      <p className="text-xs text-gray-500 mb-2">Logs (last 20 lines)</p>
                      <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono max-h-64 overflow-y-auto">
                        {trainingLogs}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {trainingError && !isTraining && (
                <div className="space-y-3">
                  <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
                    {trainingError}
                  </div>
                  <button
                    onClick={() => { setTrainingError(null); setTrainingStatus(null); setTrainingLogs('') }}
                    className="text-sm text-gray-400 hover:text-gray-300"
                  >
                    Try again
                  </button>
                </div>
              )}
            </>
          )}
        </section>

        {/* Step 2: Choose a Template */}
        {selectedModel && (
          <section className="mt-10">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-300">2. Choose a Prompt Template</h2>
              <button
                onClick={() => setShowAddTemplate(!showAddTemplate)}
                className="text-sm px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 transition-all"
              >
                {showAddTemplate ? 'Cancel' : '+ Add Template'}
              </button>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Each template has a preset prompt. <span className="text-gray-400 font-mono">trigger_keyword</span> is auto-replaced with your model's trigger word
              {selectedModel.trigger_word && (
                <span> (<span className="text-blue-400 font-mono">{selectedModel.trigger_word}</span>)</span>
              )}
            </p>

            {/* Add Template Form */}
            {showAddTemplate && (
              <form onSubmit={handleSaveTemplate} className="mb-6 p-4 rounded-lg border border-gray-800 bg-gray-900 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">Template Name</label>
                  <input
                    type="text"
                    value={newTemplateName}
                    onChange={e => setNewTemplateName(e.target.value)}
                    placeholder="e.g. Urban Street Style"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Prompt <span className="text-gray-600">(use <span className="font-mono">trigger_keyword</span> where the product goes)</span>
                  </label>
                  <textarea
                    value={newTemplatePrompt}
                    onChange={e => setNewTemplatePrompt(e.target.value)}
                    placeholder="A confident woman wearing trigger_keyword while walking down a sunlit city street..."
                    rows={4}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 resize-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">Preview Image</label>
                  {newTemplateImagePreview ? (
                    <div className="flex items-start gap-3">
                      <img src={newTemplateImagePreview} alt="Preview" className="w-32 h-32 object-cover rounded-lg border border-gray-700" />
                      <button
                        type="button"
                        onClick={() => { setNewTemplateImage(null); setNewTemplateImagePreview(null) }}
                        className="text-sm text-red-400 hover:text-red-300"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <label className="flex items-center justify-center w-full h-24 border-2 border-dashed border-gray-700 rounded-lg cursor-pointer hover:border-gray-500 transition-colors">
                      <p className="text-gray-500 text-sm">Click to upload preview image</p>
                      <input type="file" accept="image/*" onChange={handleNewTemplateImageChange} className="hidden" />
                    </label>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={savingTemplate || !newTemplateName.trim() || !newTemplatePrompt.trim() || !newTemplateImage}
                  className="w-full py-2.5 px-6 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-purple-600 hover:bg-purple-500 text-white text-sm"
                >
                  {savingTemplate ? 'Saving...' : 'Save Template'}
                </button>
              </form>
            )}

            {/* Template Grid */}
            {templatesLoading ? (
              <div className="text-center py-8">
                <div className="inline-block w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2" />
                <p className="text-gray-500 text-sm">Loading templates...</p>
              </div>
            ) : templates.length === 0 ? (
              <div className="text-center py-10 border-2 border-dashed border-gray-800 rounded-lg">
                <p className="text-gray-500">No templates yet. Add one above to get started.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {templates.map(t => {
                  const isSelected = selectedTemplate?.id === t.id
                  return (
                    <div
                      key={t.id}
                      className={`relative group rounded-lg border overflow-hidden cursor-pointer transition-all ${
                        isSelected
                          ? 'border-blue-500 ring-1 ring-blue-500/50'
                          : 'border-gray-800 hover:border-gray-600'
                      }`}
                      onClick={() => setSelectedTemplate(t)}
                    >
                      <img
                        src={t.image_url}
                        alt={t.name}
                        className="w-full aspect-square object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                      <div className="absolute bottom-0 left-0 right-0 p-3">
                        <p className="text-sm font-medium text-white truncate">{t.name}</p>
                        <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{t.prompt}</p>
                      </div>
                      {isSelected && (
                        <div className="absolute top-2 right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                          <span className="text-white text-xs">&#10003;</span>
                        </div>
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteTemplate(t.id) }}
                        className="absolute top-2 left-2 w-6 h-6 bg-red-600/80 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Delete template"
                      >
                        <span className="text-white text-xs">&times;</span>
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </section>
        )}

        {/* Step 3: Generate Image */}
        {selectedModel && (
          <section className="mt-10">
            <h2 className="text-lg font-semibold mb-2 text-gray-300">3. Generate Image</h2>
            <p className="text-sm text-gray-500 mb-4">
              Using: <span className="font-mono text-gray-400">{selectedModel.model_string}</span>
            </p>

            <form onSubmit={handleGenerate} className="space-y-6">
              {/* Pipeline Status */}
              {(generating || upscaling) && (
                <div className="flex items-center gap-3 p-4 rounded-lg border border-blue-800 bg-blue-900/20">
                  <span className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin shrink-0" />
                  <div>
                    <p className="font-medium text-blue-300">
                      {generating && 'Generating image with Flux LoRA...'}
                      {upscaling && 'Upscaling & enhancing image...'}
                    </p>
                    <div className="flex gap-2 mt-2">
                      {[
                        { label: 'Generate', done: !generating && (generatedImage || upscaling), active: generating },
                        { label: 'Upscale', done: !!upscaledImage, active: upscaling },
                      ].map((step, i) => (
                        <span key={i} className={`text-xs px-2 py-0.5 rounded-full border ${
                          step.active
                            ? 'border-blue-500 bg-blue-500/20 text-blue-300'
                            : step.done
                              ? 'border-green-700 bg-green-900/30 text-green-400'
                              : 'border-gray-700 bg-gray-800/50 text-gray-500'
                        }`}>
                          {step.done && !step.active ? '\u2713 ' : ''}{step.label}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Prompt (editable, pre-filled from template) */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Prompt
                  {selectedTemplate && (
                    <span className="text-gray-600 ml-2">(from template: {selectedTemplate.name})</span>
                  )}
                </label>
                <textarea
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder="Select a template above, or type your prompt manually..."
                  rows={4}
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

            {genError && (
              <div className="mt-6 bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
                {genError}
              </div>
            )}

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

        {/* Step 4: Upscale */}
        {generatedImage && (
          <section className="mt-10">
            <h2 className="text-lg font-semibold mb-4 text-gray-300">4. Upscale & Enhance</h2>
            <p className="text-sm text-gray-500 mb-4">
              Uses Gemini to auto-generate an enhancement prompt, then runs Clarity Upscaler for photorealistic results.
            </p>

            <button
              onClick={handleUpscale}
              disabled={upscaling}
              className="py-3 px-6 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              {upscaling ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Upscaling...
                </span>
              ) : (
                'Upscale & Enhance'
              )}
            </button>

            {upscaleError && (
              <div className="mt-4 bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
                {upscaleError}
              </div>
            )}

            {upscaledImage && (
              <div className="mt-6 space-y-6">
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-2">Original</p>
                    <img src={generatedImage} alt="Original" className="w-full rounded-lg border border-gray-800" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-2">Upscaled</p>
                    <img src={upscaledImage} alt="Upscaled" className="w-full rounded-lg border border-emerald-800" />
                  </div>
                </div>

                <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
                  <p className="text-xs text-gray-500 font-medium">Gemini-generated prompts</p>
                  <div>
                    <p className="text-xs text-gray-600">Prompt</p>
                    <p className="text-sm text-gray-300 mt-1">{upscalePrompt}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600">Negative Prompt</p>
                    <p className="text-sm text-gray-400 mt-1">{upscaleNegPrompt}</p>
                  </div>
                </div>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

export default App
