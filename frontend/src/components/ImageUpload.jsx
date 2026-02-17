import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, Image as ImageIcon } from 'lucide-react'
import { uploadImages } from '../services/api'

export default function ImageUpload({ onImagesUploaded }) {
  const [uploading, setUploading] = useState(false)
  const [images, setImages] = useState([])

  const onDrop = useCallback(async (acceptedFiles) => {
    setUploading(true)

    try {
      const uploadedFiles = await uploadImages(acceptedFiles)
      const newImages = acceptedFiles.map((file, index) => ({
        file,
        preview: URL.createObjectURL(file),
        uploaded: uploadedFiles.files[index]
      }))

      setImages([...images, ...newImages])
      onImagesUploaded([...images, ...newImages])
    } catch (error) {
      console.error('Upload error:', error)
      alert('Failed to upload images. Please try again.')
    } finally {
      setUploading(false)
    }
  }, [images, onImagesUploaded])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.webp']
    },
    multiple: true
  })

  const removeImage = (index) => {
    const newImages = images.filter((_, i) => i !== index)
    setImages(newImages)
    onImagesUploaded(newImages)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Upload Product Images</h2>
        <p className="text-gray-600">
          Upload high-quality images of your product. Multiple angles work best.
        </p>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-4">
          <div className="bg-primary-100 p-4 rounded-full">
            <Upload className="w-8 h-8 text-primary-600" />
          </div>

          {isDragActive ? (
            <p className="text-lg font-semibold text-primary-600">
              Drop images here...
            </p>
          ) : (
            <>
              <div>
                <p className="text-lg font-semibold text-gray-700">
                  Drag & drop images here
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  or click to browse files
                </p>
              </div>
              <p className="text-xs text-gray-400">
                Supports PNG, JPG, JPEG, WEBP (max 50MB)
              </p>
            </>
          )}
        </div>
      </div>

      {/* Uploading State */}
      {uploading && (
        <div className="flex items-center justify-center gap-3 text-primary-600">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-primary-600 border-t-transparent" />
          <span className="font-medium">Uploading images...</span>
        </div>
      )}

      {/* Preview Grid */}
      {images.length > 0 && (
        <div>
          <h3 className="font-semibold mb-3 text-gray-700">
            Uploaded Images ({images.length})
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {images.map((image, index) => (
              <div
                key={index}
                className="relative group rounded-lg overflow-hidden border-2 border-gray-200 hover:border-primary-400 transition-all"
              >
                <img
                  src={image.preview}
                  alt={`Product ${index + 1}`}
                  className="w-full h-40 object-cover"
                />

                <button
                  onClick={() => removeImage(index)}
                  className="absolute top-2 right-2 bg-red-500 text-white p-1.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                >
                  <X className="w-4 h-4" />
                </button>

                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
                  <div className="flex items-center gap-1 text-white text-xs">
                    <ImageIcon className="w-3 h-3" />
                    <span>{image.file.name}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
