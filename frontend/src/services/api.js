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
