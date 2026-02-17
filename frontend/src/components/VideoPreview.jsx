import { Play, Image, User, Mic, FileText } from 'lucide-react'

export default function VideoPreview({ productData, avatarData, images, onGenerate }) {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Review & Generate</h2>
        <p className="text-gray-600">
          Review your selections and generate your marketing video
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Product Info */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
            <FileText className="w-5 h-5" />
            Product Information
          </div>

          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <div>
              <div className="text-xs text-gray-500 uppercase mb-1">
                Product Name
              </div>
              <div className="font-semibold text-gray-900">
                {productData.productName}
              </div>
            </div>

            <div>
              <div className="text-xs text-gray-500 uppercase mb-1">
                Description
              </div>
              <div className="text-sm text-gray-700">
                {productData.description}
              </div>
            </div>

            <div>
              <div className="text-xs text-gray-500 uppercase mb-1">
                Video Style
              </div>
              <div className="inline-flex items-center px-3 py-1 rounded-full bg-primary-100 text-primary-700 text-sm font-medium capitalize">
                {productData.videoStyle}
              </div>
            </div>

            {productData.script && (
              <div>
                <div className="text-xs text-gray-500 uppercase mb-1">
                  Custom Script
                </div>
                <div className="text-sm text-gray-700 bg-white p-3 rounded border border-gray-200 max-h-32 overflow-y-auto">
                  {productData.script}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Avatar & Voice */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
            <User className="w-5 h-5" />
            Avatar & Voice
          </div>

          <div className="bg-gray-50 rounded-lg p-4 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary-400 to-purple-500 flex items-center justify-center">
                <User className="w-6 h-6 text-white" />
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase">Avatar</div>
                <div className="font-semibold text-gray-900">
                  {avatarData.avatarId === 'default'
                    ? 'Professional Avatar'
                    : avatarData.avatarId}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center">
                <Mic className="w-6 h-6 text-white" />
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase">Voice</div>
                <div className="font-semibold text-gray-900">
                  {avatarData.voiceId === 'default'
                    ? 'Professional Voice'
                    : avatarData.voiceId}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Images Preview */}
      <div>
        <div className="flex items-center gap-2 text-lg font-semibold text-gray-900 mb-4">
          <Image className="w-5 h-5" />
          Product Images ({images.length})
        </div>

        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {images.slice(0, 6).map((image, index) => (
            <div
              key={index}
              className="aspect-square rounded-lg overflow-hidden border-2 border-gray-200"
            >
              <img
                src={image.preview}
                alt={`Product ${index + 1}`}
                className="w-full h-full object-cover"
              />
            </div>
          ))}
        </div>
      </div>

      {/* Generate Button */}
      <div className="pt-6 border-t border-gray-200">
        <button
          onClick={onGenerate}
          className="btn-primary w-full flex items-center justify-center gap-3 text-lg py-4"
        >
          <Play className="w-6 h-6" />
          Generate Marketing Video
        </button>

        <p className="text-center text-sm text-gray-500 mt-4">
          Video generation typically takes 2-5 minutes
        </p>
      </div>
    </div>
  )
}
