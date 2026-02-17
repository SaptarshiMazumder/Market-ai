import { CheckCircle, AlertCircle, Loader } from 'lucide-react'

export default function GenerationProgress({ status, jobId }) {
  if (!status) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent" />
      </div>
    )
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case 'completed':
        return <CheckCircle className="w-16 h-16 text-green-500" />
      case 'failed':
        return <AlertCircle className="w-16 h-16 text-red-500" />
      default:
        return (
          <div className="relative">
            <Loader className="w-16 h-16 text-primary-600 animate-spin" />
          </div>
        )
    }
  }

  const getStatusColor = () => {
    switch (status.status) {
      case 'completed':
        return 'bg-green-500'
      case 'failed':
        return 'bg-red-500'
      default:
        return 'bg-primary-600'
    }
  }

  return (
    <div className="py-12 space-y-8">
      <div className="flex flex-col items-center gap-4">
        {getStatusIcon()}

        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            {status.status === 'completed'
              ? 'Video Ready!'
              : status.status === 'failed'
              ? 'Generation Failed'
              : 'Generating Your Video'}
          </h2>
          <p className="text-gray-600">{status.message}</p>
        </div>
      </div>

      {/* Progress Bar */}
      {status.status === 'processing' && (
        <div className="max-w-md mx-auto">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Progress</span>
            <span>{status.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full ${getStatusColor()} transition-all duration-500 rounded-full`}
              style={{ width: `${status.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Completed - Download Button */}
      {status.status === 'completed' && (
        <div className="flex flex-col items-center gap-4">
          <a
            href={status.video_url}
            download
            className="btn-primary inline-flex items-center gap-2"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Download Video
          </a>

          <button
            onClick={() => window.location.reload()}
            className="btn-secondary"
          >
            Create Another Video
          </button>
        </div>
      )}

      {/* Failed - Retry */}
      {status.status === 'failed' && (
        <div className="flex flex-col items-center gap-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 max-w-md">
            <p className="text-sm text-red-800">
              {status.message || 'An error occurred during video generation.'}
            </p>
          </div>

          <button
            onClick={() => window.location.reload()}
            className="btn-primary"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Job ID */}
      <div className="text-center">
        <p className="text-xs text-gray-400">
          Job ID: <code className="bg-gray-100 px-2 py-1 rounded">{jobId}</code>
        </p>
      </div>
    </div>
  )
}
