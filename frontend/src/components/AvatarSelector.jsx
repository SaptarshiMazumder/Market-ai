import { useState, useEffect } from 'react'
import { User, Mic } from 'lucide-react'
import { getAvatars, getVoices } from '../services/api'

export default function AvatarSelector({ data, onChange }) {
  const [avatars, setAvatars] = useState([])
  const [voices, setVoices] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadOptions()
  }, [])

  const loadOptions = async () => {
    try {
      const [avatarData, voiceData] = await Promise.all([
        getAvatars(),
        getVoices()
      ])

      setAvatars(avatarData.avatars || [])
      setVoices(voiceData.voices || [])
    } catch (error) {
      console.error('Error loading options:', error)
    } finally {
      setLoading(false)
    }
  }

  const updateField = (field, value) => {
    onChange({ ...data, [field]: value })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold mb-2">Customize Avatar & Voice</h2>
        <p className="text-gray-600">
          Choose an AI avatar and voice for your marketing video
        </p>
      </div>

      {/* Avatar Selection */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-3">
          <User className="w-4 h-4 inline mr-2" />
          Select Avatar
        </label>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {avatars.map((avatar) => (
            <button
              key={avatar.avatar_id}
              onClick={() => updateField('avatarId', avatar.avatar_id)}
              className={`p-4 rounded-lg border-2 text-left transition-all ${
                data.avatarId === avatar.avatar_id
                  ? 'border-primary-500 bg-primary-50 shadow-md'
                  : 'border-gray-200 hover:border-gray-300 hover:shadow'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary-400 to-purple-500 flex items-center justify-center">
                  <User className="w-8 h-8 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-gray-900">
                    {avatar.avatar_name}
                  </div>
                  <div className="text-sm text-gray-500 capitalize">
                    {avatar.gender}
                  </div>
                </div>
              </div>
            </button>
          ))}

          {avatars.length === 0 && (
            <div className="col-span-2 text-center py-8 text-gray-500">
              Using default professional avatar
            </div>
          )}
        </div>
      </div>

      {/* Voice Selection */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-3">
          <Mic className="w-4 h-4 inline mr-2" />
          Select Voice
        </label>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {voices.map((voice) => (
            <button
              key={voice.voice_id}
              onClick={() => updateField('voiceId', voice.voice_id)}
              className={`p-4 rounded-lg border-2 text-left transition-all ${
                data.voiceId === voice.voice_id
                  ? 'border-primary-500 bg-primary-50 shadow-md'
                  : 'border-gray-200 hover:border-gray-300 hover:shadow'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center">
                  <Mic className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-gray-900">{voice.name}</div>
                  <div className="text-sm text-gray-500 capitalize">
                    {voice.labels?.accent} • {voice.labels?.gender}
                  </div>
                </div>
              </div>
            </button>
          ))}

          {voices.length === 0 && (
            <div className="col-span-2 text-center py-8 text-gray-500">
              Using default professional voice
            </div>
          )}
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <span className="font-semibold">Pro Tip:</span> Choose an avatar and
          voice that match your brand personality and target audience for best
          results.
        </p>
      </div>
    </div>
  )
}
