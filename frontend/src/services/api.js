import axios from 'axios'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Health check
export const healthCheck = async () => {
  const { data } = await api.get('/health')
  return data
}

// Upload image
export const uploadImage = async (file) => {
  const formData = new FormData()
  formData.append('image', file)
  const { data } = await api.post('/upload-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return data
}

// Generate image (quick mode)
export const generateImage = async (productDescription, style, referenceImage) => {
  const { data } = await api.post('/generate-image', {
    productDescription, style, referenceImage
  })
  return data
}

// Get job status
export const getStatus = async (jobId) => {
  const { data } = await api.get(`/status/${jobId}`)
  return data
}

// === Product Pipeline ===

export const registerProduct = async (productName) => {
  const { data } = await api.post('/products/register', { product_name: productName })
  return data
}

export const uploadTrainingData = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/products/upload-training-data', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return data
}

export const startTraining = async (productName, zipUrl, uploadedFile) => {
  const payload = { product_name: productName }
  if (zipUrl) payload.zip_url = zipUrl
  if (uploadedFile) payload.uploaded_file = uploadedFile
  const { data } = await api.post('/products/train', payload)
  return data
}

export const getTrainingStatus = async (trainingId) => {
  const { data } = await api.get(`/products/train-status/${trainingId}`)
  return data
}

export const listProducts = async () => {
  const { data } = await api.get('/products')
  return data
}

export const listTrainedProducts = async () => {
  const { data } = await api.get('/products/trained')
  return data
}

// === Generation ===

export const generateMask = async (templateUrl, objectDescription) => {
  const { data } = await api.post('/generate/mask', {
    template_url: templateUrl,
    object_description: objectDescription
  })
  return data
}

export const inpaint = async (templateUrl, maskUrl, productName, productDescription) => {
  const { data } = await api.post('/generate/inpaint', {
    template_url: templateUrl,
    mask_url: maskUrl,
    product_name: productName,
    product_description: productDescription
  })
  return data
}

export const runPipeline = async (templateUrl, productName, objectDescription, productDescription) => {
  const { data } = await api.post('/generate/pipeline', {
    template_url: templateUrl,
    product_name: productName,
    object_description: objectDescription,
    product_description: productDescription
  })
  return data
}

// === Batch ===

export const startBatch = async (productName, templateUrls) => {
  const { data } = await api.post('/batch/start', {
    product_name: productName,
    template_urls: templateUrls
  })
  return data
}

export const getBatchStatus = async (batchJobId) => {
  const { data } = await api.get(`/batch/status/${batchJobId}`)
  return data
}

// === Flux LoRA Generation ===

export const listReplicateModels = async () => {
  const { data } = await api.get('/products/replicate/list-models')
  return data
}

export const getModelDetails = async (modelName) => {
  const { data } = await api.get(`/products/replicate/model-details/${modelName}`)
  return data
}

export const importFromReplicate = async (modelName, productName, versionIndex, triggerWord) => {
  const payload = { model_name: modelName }
  if (productName) payload.product_name = productName
  if (versionIndex !== undefined) payload.version_index = versionIndex
  if (triggerWord) payload.trigger_word = triggerWord
  const { data } = await api.post('/products/import-from-replicate', payload)
  return data
}

export const generateWithFluxLora = async (params) => {
  const { data } = await api.post('/generate/flux-lora', params)
  return data
}

export const generateWithFluxLoraImg2Img = async (params) => {
  const { data } = await api.post('/generate/flux-lora-img2img', params)
  return data
}

export default api
