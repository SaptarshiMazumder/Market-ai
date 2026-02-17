import { Video } from 'lucide-react'

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50 backdrop-blur-lg bg-white/90">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-primary-500 to-purple-600 p-2 rounded-lg">
              <Video className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">MarketAI</h1>
              <p className="text-xs text-gray-500">Video Generator</p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6">
            <a href="#" className="text-gray-600 hover:text-primary-600 transition-colors">
              Dashboard
            </a>
            <a href="#" className="text-gray-600 hover:text-primary-600 transition-colors">
              Templates
            </a>
            <a href="#" className="text-gray-600 hover:text-primary-600 transition-colors">
              Library
            </a>
          </nav>
        </div>
      </div>
    </header>
  )
}
