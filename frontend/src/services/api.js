import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ── Templates ──────────────────────────────────────────────────────────────

export const listTemplates = async () => {
  const { data } = await api.get('/templates')
  return data
}

export const createTemplate = async (name, prompt, imageFile) => {
  const formData = new FormData()
  formData.append('name', name)
  formData.append('prompt', prompt)
  formData.append('image', imageFile)
  const { data } = await api.post('/templates', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const deleteTemplate = async (templateId) => {
  const { data } = await api.delete(`/templates/${templateId}`)
  return data
}

// ── Z-Turbo Image Generation ───────────────────────────────────────────────

export const generateImage = async ({ prompt, width, height, steps, cfg, denoise, seed }) => {
  const payload = { prompt, width, height, steps, cfg, denoise }
  if (seed !== undefined && seed !== null && seed !== '') payload.seed = seed
  const { data } = await api.post('/z-turbo/generate', payload)
  return data
}

export const generateImageAsync = async ({ prompt, width, height, steps, cfg, denoise, seed }) => {
  const payload = { prompt, width, height, steps, cfg, denoise }
  if (seed !== undefined && seed !== null && seed !== '') payload.seed = seed
  const { data } = await api.post('/z-turbo/generate/async', payload)
  return data
}

export const getGenerationJob = async (jobId) => {
  const { data } = await api.get(`/z-turbo/generate/${jobId}`)
  return data
}

// ── Training ───────────────────────────────────────────────────────────────

export const listModels = async () => {
  const { data } = await api.get('/models')
  return data
}

export const getTrainingConfig = async () => {
  const { data } = await api.get('/training-config')
  return data
}

export const startTraining = async (formData) => {
  const { data } = await api.post('/train', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const getTrainingStatus = async (jobId) => {
  const { data } = await api.get(`/training-status/${jobId}`)
  return data
}

export default api
