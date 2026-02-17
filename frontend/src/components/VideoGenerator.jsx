import { useState, useEffect } from 'react'
import ImageUpload from './ImageUpload'
import ProductDetails from './ProductDetails'
import AvatarSelector from './AvatarSelector'
import GenerationProgress from './GenerationProgress'
import VideoPreview from './VideoPreview'
import { generateVideo, getStatus } from '../services/api'

const STEPS = [
  { id: 1, name: 'Upload Images', component: 'upload' },
  { id: 2, name: 'Product Details', component: 'details' },
  { id: 3, name: 'Customize Avatar', component: 'avatar' },
  { id: 4, name: 'Generate Video', component: 'generate' }
]

export default function VideoGenerator() {
  const [currentStep, setCurrentStep] = useState(1)
  const [uploadedImages, setUploadedImages] = useState([])
  const [productData, setProductData] = useState({
    productName: '',
    description: '',
    script: '',
    videoStyle: 'professional'
  })
  const [avatarData, setAvatarData] = useState({
    avatarId: 'default',
    voiceId: 'default'
  })
  const [jobId, setJobId] = useState(null)
  const [generationStatus, setGenerationStatus] = useState(null)
  const [isGenerating, setIsGenerating] = useState(false)

  // Poll for job status
  useEffect(() => {
    if (!jobId || !isGenerating) return

    const interval = setInterval(async () => {
      try {
        const status = await getStatus(jobId)
        setGenerationStatus(status)

        if (status.status === 'completed' || status.status === 'failed') {
          setIsGenerating(false)
          clearInterval(interval)
        }
      } catch (error) {
        console.error('Error polling status:', error)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [jobId, isGenerating])

  const handleImagesUploaded = (images) => {
    setUploadedImages(images)
  }

  const handleNext = () => {
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleGenerate = async () => {
    try {
      setIsGenerating(true)

      const response = await generateVideo({
        ...productData,
        ...avatarData,
        images: uploadedImages
      })

      setJobId(response.job_id)
      setGenerationStatus({
        status: 'queued',
        progress: 0,
        message: 'Starting video generation...'
      })
    } catch (error) {
      console.error('Error generating video:', error)
      setIsGenerating(false)
      alert('Failed to start video generation. Please try again.')
    }
  }

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return uploadedImages.length > 0
      case 2:
        return productData.productName && productData.description
      case 3:
        return true
      default:
        return false
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return <ImageUpload onImagesUploaded={handleImagesUploaded} />

      case 2:
        return (
          <ProductDetails
            data={productData}
            onChange={setProductData}
          />
        )

      case 3:
        return (
          <AvatarSelector
            data={avatarData}
            onChange={setAvatarData}
          />
        )

      case 4:
        if (isGenerating || generationStatus) {
          return (
            <GenerationProgress
              status={generationStatus}
              jobId={jobId}
            />
          )
        }
        return (
          <VideoPreview
            productData={productData}
            avatarData={avatarData}
            images={uploadedImages}
            onGenerate={handleGenerate}
          />
        )

      default:
        return null
    }
  }

  return (
    <div className="space-y-8">
      {/* Progress Steps */}
      <div className="flex items-center justify-between max-w-3xl mx-auto">
        {STEPS.map((step, index) => (
          <div key={step.id} className="flex items-center flex-1">
            <div className="flex flex-col items-center flex-1">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
                  currentStep >= step.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-200 text-gray-500'
                }`}
              >
                {step.id}
              </div>
              <span
                className={`text-sm mt-2 font-medium ${
                  currentStep >= step.id ? 'text-primary-600' : 'text-gray-500'
                }`}
              >
                {step.name}
              </span>
            </div>

            {index < STEPS.length - 1 && (
              <div
                className={`h-1 flex-1 mx-4 rounded ${
                  currentStep > step.id ? 'bg-primary-600' : 'bg-gray-200'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="card max-w-4xl mx-auto min-h-[500px]">
        {renderStepContent()}
      </div>

      {/* Navigation Buttons */}
      {!isGenerating && !generationStatus && (
        <div className="flex justify-between max-w-4xl mx-auto">
          <button
            onClick={handleBack}
            disabled={currentStep === 1}
            className="btn-secondary disabled:opacity-50"
          >
            Back
          </button>

          <button
            onClick={handleNext}
            disabled={!canProceed()}
            className="btn-primary disabled:opacity-50"
          >
            {currentStep === STEPS.length ? 'Review' : 'Next Step'}
          </button>
        </div>
      )}
    </div>
  )
}
