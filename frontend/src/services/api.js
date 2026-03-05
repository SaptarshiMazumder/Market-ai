export async function listTemplates() {
  const res = await fetch('/api/templates')
  if (!res.ok) throw new Error('Failed to fetch templates')
  const data = await res.json()
  return data.templates
}

export async function submitWithTemplate({ subject, scenario, lora_name, keyword, ...params }) {
  const res = await fetch('/api/generate/image/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, scenario, lora_name, keyword, ...params }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || 'Failed to submit generation job')
  }
  return res.json()
}

export async function submitNoTemplate({ subject, scenario, ...params }) {
  const res = await fetch('/api/generate/image/submit/no-template', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, scenario, ...params }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || 'Failed to submit generation job')
  }
  return res.json()
}

export async function pollGenerate(jobId) {
  const res = await fetch(`/api/generate/image/status/${jobId}`)
  if (!res.ok) throw new Error('Failed to poll job status')
  return res.json()
}

export async function uploadMaskImage(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/mask/upload', { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || 'Failed to upload image')
  }
  return res.json() // { r2_path }
}

export async function submitMask({ image_url, object_name, ...params }) {
  const res = await fetch('/api/mask/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_url, object_name, ...params }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || 'Failed to submit masking job')
  }
  return res.json()
}

export async function pollMask(jobId) {
  const res = await fetch(`/api/mask/status/${jobId}`)
  if (!res.ok) throw new Error('Failed to poll mask job status')
  return res.json()
}

export async function listProductImages() {
  const res = await fetch('/api/generate/image/list')
  if (!res.ok) throw new Error('Failed to list generated images')
  const data = await res.json()
  return data.images
}

export async function listMaskedImages() {
  const res = await fetch('/api/mask/list')
  if (!res.ok) throw new Error('Failed to list masked images')
  const data = await res.json()
  return data.images
}

export async function submitInpaint({ scene_url, reference_url, ...params }) {
  const res = await fetch('/api/inpaint/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scene_url, reference_url, ...params }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || 'Failed to submit inpainting job')
  }
  return res.json()
}

export async function pollInpaint(jobId) {
  const res = await fetch(`/api/inpaint/status/${jobId}`)
  if (!res.ok) throw new Error('Failed to poll inpaint job status')
  return res.json()
}

// ── Pipeline (port 5009) ────────────────────────────────────────────────────

export async function uploadProductImage(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/pipeline/upload', { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || 'Failed to upload product image')
  }
  return res.json() // { r2_path, preview_url }
}

export async function submitPipeline({ subject, mode, product_r2, lora_name, keyword, template_name, preview_image_url, run_masking, run_inpainting }) {
  const res = await fetch('/api/pipeline/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, mode, product_r2, lora_name, keyword, template_name, preview_image_url, run_masking, run_inpainting }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || 'Failed to submit pipeline')
  }
  return res.json() // { pipeline_id, status }
}

export async function getPipelineStatus(pipelineId) {
  const res = await fetch(`/api/pipeline/status/${pipelineId}`)
  if (!res.ok) throw new Error('Failed to get pipeline status')
  return res.json()
}

export async function listPipelines() {
  const res = await fetch('/api/pipeline/list')
  if (!res.ok) throw new Error('Failed to list pipelines')
  const data = await res.json()
  return data.pipelines
}

export async function getPipelineQueues() {
  const res = await fetch('/api/pipeline/queues')
  if (!res.ok) throw new Error('Failed to get queue counts')
  return res.json()
}
