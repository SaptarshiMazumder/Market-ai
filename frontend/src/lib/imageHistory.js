const GENERATED_KEY = 'market_ai_generated_images'
const MASKED_KEY = 'market_ai_masked_images'
const MAX_ENTRIES = 20

function _save(key, entry, load) {
  const history = load()
  history.unshift({ ...entry, timestamp: Date.now() })
  localStorage.setItem(key, JSON.stringify(history.slice(0, MAX_ENTRIES)))
}

function _load(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || '[]')
  } catch {
    return []
  }
}

export function saveGeneratedImage({ r2_path, preview_url, subject }) {
  _save(GENERATED_KEY, { r2_path, preview_url, subject }, loadImageHistory)
}

export function loadImageHistory() {
  return _load(GENERATED_KEY)
}

export function saveMaskedImage({ r2_path, preview_url, object_name }) {
  _save(MASKED_KEY, { r2_path, preview_url, object_name }, loadMaskHistory)
}

export function loadMaskHistory() {
  return _load(MASKED_KEY)
}
