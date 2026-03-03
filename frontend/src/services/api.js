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
