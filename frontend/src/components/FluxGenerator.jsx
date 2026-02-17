import { useState, useEffect } from 'react'
import { Download, RefreshCw, Sparkles, Settings, Image as ImageIcon, Loader2 } from 'lucide-react'
import {
  listReplicateModels,
  importFromReplicate,
  generateWithFluxLora,
  listTrainedProducts
} from '../services/api'

export default function FluxGenerator() {
  const [step, setStep] = useState('select') // 'select', 'generate', 'result'

  // Model selection
  const [replicateModels, setReplicateModels] = useState([])
  const [localProducts, setLocalProducts] = useState([])
  const [loadingModels, setLoadingModels] = useState(false)
  const [selectedModel, setSelectedModel] = useState(null)
  const [importing, setImporting] = useState(false)

  // Generation params
  const [prompt, setPrompt] = useState('')
  const [loraScale, setLoraScale] = useState(0.9)
  const [numInferenceSteps, setNumInferenceSteps] = useState(28)
  const [guidanceScale, setGuidanceScale] = useState(3.5)
  const [width, setWidth] = useState(1024)
  const [height, setHeight] = useState(1024)
  const [numOutputs, setNumOutputs] = useState(1)
  const [outputFormat, setOutputFormat] = useState('png')
  const [seed, setSeed] = useState('')

  // Results
  const [generating, setGenerating] = useState(false)
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    loadLocalProducts()
  }, [])

  const loadLocalProducts = async () => {
    try {
      const data = await listTrainedProducts()
      setLocalProducts(data.products || [])
    } catch (err) {
      console.error('Error loading local products:', err)
    }
  }

  const loadReplicateModels = async () => {
    setLoadingModels(true)
    setError(null)
    try {
      const data = await listReplicateModels()
      setReplicateModels(data.models || [])
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load models from Replicate')
    } finally {
      setLoadingModels(false)
    }
  }

  const handleImportModel = async (modelName) => {
    setImporting(true)
    setError(null)
    try {
      const data = await importFromReplicate(modelName)
      alert(`Successfully imported: ${data.product_name}`)
      await loadLocalProducts()
      setStep('select')
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to import model')
    } finally {
      setImporting(false)
    }
  }

  const handleSelectProduct = (product) => {
    setSelectedModel(product)
    setStep('generate')
  }

  const handleGenerate = async () => {
    if (!selectedModel) return

    setGenerating(true)
    setError(null)
    setResults([])

    try {
      const params = {
        product_name: selectedModel.product_name,
        prompt: prompt,
        lora_scale: loraScale,
        num_inference_steps: numInferenceSteps,
        guidance_scale: guidanceScale,
        width: parseInt(width),
        height: parseInt(height),
        num_outputs: parseInt(numOutputs),
        output_format: outputFormat
      }

      if (seed) params.seed = parseInt(seed)

      const data = await generateWithFluxLora(params)
      setResults(data.results || [])
      setStep('result')
    } catch (err) {
      setError(err.response?.data?.error || 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Step Indicator */}
      <div className="flex items-center justify-center gap-4">
        <div className={`flex items-center gap-2 ${step === 'select' ? 'text-blue-600' : 'text-gray-400'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            step === 'select' ? 'bg-blue-600 text-white' : 'bg-gray-200'
          }`}>1</div>
          <span className="font-semibold">Select Model</span>
        </div>
        <div className="w-12 h-0.5 bg-gray-300"></div>
        <div className={`flex items-center gap-2 ${step === 'generate' ? 'text-blue-600' : 'text-gray-400'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            step === 'generate' ? 'bg-blue-600 text-white' : 'bg-gray-200'
          }`}>2</div>
          <span className="font-semibold">Generate</span>
        </div>
        <div className="w-12 h-0.5 bg-gray-300"></div>
        <div className={`flex items-center gap-2 ${step === 'result' ? 'text-blue-600' : 'text-gray-400'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            step === 'result' ? 'bg-blue-600 text-white' : 'bg-gray-200'
          }`}>3</div>
          <span className="font-semibold">Results</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* STEP 1: Select Model */}
      {step === 'select' && (
        <div className="space-y-6">
          {/* Local Products */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Your Imported Models</h3>
              <button
                onClick={loadLocalProducts}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>

            {localProducts.length === 0 ? (
              <p className="text-gray-500 text-sm">No models imported yet. Import from Replicate below.</p>
            ) : (
              <div className="grid gap-3">
                {localProducts.map((product) => (
                  <div
                    key={product.product_name}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
                  >
                    <div>
                      <h4 className="font-semibold text-gray-900">{product.product_name}</h4>
                      <p className="text-sm text-gray-500">Trigger: {product.trigger_word}</p>
                      <p className="text-xs text-gray-400 mt-1">Model: {product.model_slug}</p>
                    </div>
                    <button
                      onClick={() => handleSelectProduct(product)}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Use This Model
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Replicate Models */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Import from Replicate</h3>
              <button
                onClick={loadReplicateModels}
                disabled={loadingModels}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors flex items-center gap-2"
              >
                {loadingModels ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4" />
                    Fetch Models
                  </>
                )}
              </button>
            </div>

            {replicateModels.length === 0 ? (
              <p className="text-gray-500 text-sm">
                Click "Fetch Models" to load your trained models from Replicate.
              </p>
            ) : (
              <div className="grid gap-3">
                {replicateModels.map((model) => (
                  <div
                    key={model.full_name}
                    className="p-4 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900">{model.name}</h4>
                        <p className="text-sm text-gray-500">{model.full_name}</p>
                        <p className="text-xs text-gray-400 mt-2">
                          {model.versions.length} version{model.versions.length !== 1 ? 's' : ''}
                          {model.trigger_word && ` • Trigger: ${model.trigger_word}`}
                        </p>
                      </div>
                      <button
                        onClick={() => handleImportModel(model.name)}
                        disabled={importing}
                        className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                      >
                        {importing ? 'Importing...' : 'Import'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* STEP 2: Generate */}
      {step === 'generate' && selectedModel && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selectedModel.product_name}</h3>
                <p className="text-sm text-gray-500">Trigger: {selectedModel.trigger_word}</p>
              </div>
              <button
                onClick={() => setStep('select')}
                className="text-sm text-gray-600 hover:text-gray-800"
              >
                Change Model
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {/* Prompt */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Prompt *
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="professional product photo, white background, studio lighting"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
              />
              <p className="text-xs text-gray-500 mt-1">
                The trigger word "{selectedModel.trigger_word}" will be automatically added
              </p>
            </div>

            {/* Advanced Settings */}
            <details className="border border-gray-200 rounded-lg">
              <summary className="px-4 py-3 cursor-pointer hover:bg-gray-50 flex items-center gap-2">
                <Settings className="w-4 h-4" />
                <span className="font-semibold">Advanced Settings</span>
              </summary>
              <div className="p-4 space-y-4 border-t border-gray-200">
                {/* LoRA Scale */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    LoRA Scale: {loraScale}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={loraScale}
                    onChange={(e) => setLoraScale(parseFloat(e.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500">How strong the LoRA effect is (0.0 - 1.0)</p>
                </div>

                {/* Inference Steps */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Inference Steps: {numInferenceSteps}
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="50"
                    step="1"
                    value={numInferenceSteps}
                    onChange={(e) => setNumInferenceSteps(parseInt(e.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500">More steps = better quality but slower</p>
                </div>

                {/* Guidance Scale */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Guidance Scale: {guidanceScale}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="0.5"
                    value={guidanceScale}
                    onChange={(e) => setGuidanceScale(parseFloat(e.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500">How closely to follow the prompt</p>
                </div>

                {/* Dimensions */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Width</label>
                    <select
                      value={width}
                      onChange={(e) => setWidth(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="512">512</option>
                      <option value="768">768</option>
                      <option value="1024">1024</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Height</label>
                    <select
                      value={height}
                      onChange={(e) => setHeight(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="512">512</option>
                      <option value="768">768</option>
                      <option value="1024">1024</option>
                    </select>
                  </div>
                </div>

                {/* Num Outputs */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Number of Outputs
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="4"
                    value={numOutputs}
                    onChange={(e) => setNumOutputs(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                {/* Seed */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Seed (optional)
                  </label>
                  <input
                    type="number"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    placeholder="Random"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                  <p className="text-xs text-gray-500">For reproducible results</p>
                </div>
              </div>
            </details>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={!prompt || generating}
              className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
            >
              {generating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Generate Image
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Results */}
      {step === 'result' && results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Generated Images</h3>
            <button
              onClick={() => setStep('generate')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Generate Another
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {results.map((result, idx) => (
              <div key={idx} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <img
                  src={result.image_url}
                  alt={`Generated ${idx + 1}`}
                  className="w-full h-auto"
                />
                <div className="p-4">
                  <a
                    href={result.image_url}
                    download
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
