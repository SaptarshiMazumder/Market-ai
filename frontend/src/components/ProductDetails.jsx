import { Sparkles } from 'lucide-react'

const VIDEO_STYLES = [
  {
    id: 'professional',
    name: 'Professional',
    description: 'Corporate and business-oriented',
    color: 'blue'
  },
  {
    id: 'casual',
    name: 'Casual',
    description: 'Friendly and approachable',
    color: 'green'
  },
  {
    id: 'energetic',
    name: 'Energetic',
    description: 'Dynamic and exciting',
    color: 'purple'
  }
]

export default function ProductDetails({ data, onChange }) {
  const updateField = (field, value) => {
    onChange({ ...data, [field]: value })
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Product Details</h2>
        <p className="text-gray-600">
          Tell us about your product to create compelling marketing content
        </p>
      </div>

      <div className="space-y-5">
        {/* Product Name */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Product Name *
          </label>
          <input
            type="text"
            value={data.productName}
            onChange={(e) => updateField('productName', e.target.value)}
            placeholder="e.g., Premium Wireless Headphones"
            className="input-field"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Product Description *
          </label>
          <textarea
            value={data.description}
            onChange={(e) => updateField('description', e.target.value)}
            placeholder="Describe your product's key features and benefits..."
            rows={4}
            className="input-field resize-none"
          />
          <p className="text-xs text-gray-500 mt-1">
            This will be used to generate your video script
          </p>
        </div>

        {/* Video Style */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-3">
            Video Style *
          </label>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {VIDEO_STYLES.map((style) => (
              <button
                key={style.id}
                onClick={() => updateField('videoStyle', style.id)}
                className={`p-4 rounded-lg border-2 text-left transition-all ${
                  data.videoStyle === style.id
                    ? `border-${style.color}-500 bg-${style.color}-50`
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-semibold text-gray-900">{style.name}</div>
                <div className="text-sm text-gray-600 mt-1">
                  {style.description}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Script (Optional) */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Custom Script (Optional)
          </label>
          <textarea
            value={data.script}
            onChange={(e) => updateField('script', e.target.value)}
            placeholder="Leave empty to auto-generate based on description..."
            rows={6}
            className="input-field resize-none"
          />
          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
            <Sparkles className="w-3 h-3" />
            <span>AI will generate a compelling script if left empty</span>
          </div>
        </div>
      </div>
    </div>
  )
}
