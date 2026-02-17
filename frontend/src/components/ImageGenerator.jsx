import { useState } from 'react';
import { Upload, Wand2, Download, Image as ImageIcon, Loader2 } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

const ImageGenerator = () => {
  const [productDescription, setProductDescription] = useState('');
  const [style, setStyle] = useState('lifestyle');
  const [referenceImage, setReferenceImage] = useState(null);
  const [referenceImagePreview, setReferenceImagePreview] = useState(null);
  const [uploadedFilename, setUploadedFilename] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImage, setGeneratedImage] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');

  const styles = [
    { value: 'lifestyle', label: 'Lifestyle', description: 'Person using product, real-world setting' },
    { value: 'action', label: 'Action', description: 'Dynamic motion shot, sports/energy' },
    { value: 'editorial', label: 'Editorial', description: 'Magazine-style, fashion photography' },
    { value: 'outdoor', label: 'Outdoor', description: 'Nature/urban backdrop, adventure' },
    { value: 'luxury', label: 'Luxury', description: 'Premium brand campaign, elegant' },
    { value: 'studio', label: 'Studio', description: 'Clean white background, product-only' }
  ];

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setReferenceImage(file);
      setReferenceImagePreview(URL.createObjectURL(file));
      setError(null);
    }
  };

  const uploadReferenceImage = async () => {
    if (!referenceImage) return null;

    const formData = new FormData();
    formData.append('image', referenceImage);

    try {
      const response = await axios.post(`${API_URL}/upload-image`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data.filename;
    } catch (err) {
      console.error('Error uploading image:', err);
      throw new Error('Failed to upload reference image');
    }
  };

  const pollJobStatus = async (jobId) => {
    const maxAttempts = 120; // 2 minutes max
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await axios.get(`${API_URL}/status/${jobId}`);
        const status = response.data;

        setProgress(status.progress || 0);
        setProgressMessage(status.message || '');

        if (status.status === 'completed') {
          setGeneratedImage(`${API_URL}/image/${jobId}`);
          setIsGenerating(false);
          return true;
        } else if (status.status === 'failed') {
          setError(status.message || 'Generation failed');
          setIsGenerating(false);
          return true;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 1000);
        } else {
          setError('Generation timed out');
          setIsGenerating(false);
        }
      } catch (err) {
        console.error('Error polling status:', err);
        setError('Failed to check generation status');
        setIsGenerating(false);
      }
    };

    poll();
  };

  const handleGenerate = async () => {
    if (!productDescription.trim()) {
      setError('Please enter a product description');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setGeneratedImage(null);
    setProgress(0);
    setProgressMessage('Preparing...');

    try {
      // Upload reference image if provided
      let filename = null;
      if (referenceImage) {
        setProgressMessage('Uploading reference image...');
        filename = await uploadReferenceImage();
        setUploadedFilename(filename);
      }

      // Generate image
      setProgressMessage('Starting image generation...');
      const response = await axios.post(`${API_URL}/generate-image`, {
        productDescription,
        style,
        referenceImage: filename
      });

      const newJobId = response.data.job_id;
      setJobId(newJobId);

      // Poll for completion
      await pollJobStatus(newJobId);

    } catch (err) {
      console.error('Error generating image:', err);
      setError(err.response?.data?.error || 'Failed to generate image');
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (jobId) {
      window.open(`${API_URL}/download/${jobId}`, '_blank');
    }
  };

  const handleReset = () => {
    setProductDescription('');
    setStyle('professional');
    setReferenceImage(null);
    setReferenceImagePreview(null);
    setUploadedFilename(null);
    setGeneratedImage(null);
    setJobId(null);
    setError(null);
    setProgress(0);
    setProgressMessage('');
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column - Input */}
        <div>
          <h2 className="text-2xl font-bold mb-6 text-gray-900">Generate Your Image</h2>

          {/* Product Description */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Product Description *
            </label>
            <textarea
              value={productDescription}
              onChange={(e) => setProductDescription(e.target.value)}
              placeholder="e.g., luxury wristwatch with silver band and blue dial, smartwatch with black screen..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              rows="4"
            />
            <p className="text-xs text-gray-500 mt-1">
              Describe the product you want to generate
            </p>
          </div>

          {/* Style Selection */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Style
            </label>
            <div className="grid grid-cols-3 gap-2">
              {styles.map((s) => (
                <button
                  key={s.value}
                  onClick={() => setStyle(s.value)}
                  className={`p-2.5 rounded-lg border-2 text-left transition-all ${
                    style === s.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-semibold text-xs">{s.label}</div>
                  <div className="text-[10px] text-gray-500 mt-0.5">{s.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Reference Image Upload (Optional) */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Reference Image (Optional)
            </label>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
              <p className="text-xs text-blue-700">
                💡 <strong>Tip:</strong> Upload a product photo to guide the AI. It will use the composition,
                lighting, and overall style while applying your description and chosen style preset.
              </p>
            </div>
            <div className={`border-2 border-dashed rounded-lg p-6 text-center transition-all ${
              referenceImagePreview
                ? 'border-blue-400 bg-blue-50'
                : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
            }`}>
              <input
                type="file"
                accept="image/*"
                onChange={handleImageSelect}
                className="hidden"
                id="reference-upload"
              />
              <label htmlFor="reference-upload" className="cursor-pointer block">
                {referenceImagePreview ? (
                  <div>
                    <img
                      src={referenceImagePreview}
                      alt="Reference"
                      className="max-h-48 mx-auto rounded-lg mb-3 shadow-md"
                    />
                    <p className="text-sm font-medium text-blue-600">✓ Reference image loaded</p>
                    <p className="text-xs text-gray-500 mt-1">Click to change image</p>
                  </div>
                ) : (
                  <div>
                    <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <Upload className="w-8 h-8 text-blue-500" />
                    </div>
                    <p className="text-sm font-medium text-gray-700 mb-1">
                      Upload a reference product image
                    </p>
                    <p className="text-xs text-gray-500">
                      PNG, JPG, or JPEG • Max 16MB
                    </p>
                    <p className="text-xs text-blue-600 mt-2">
                      AI will maintain the style and composition
                    </p>
                  </div>
                )}
              </label>
            </div>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !productDescription.trim()}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 px-6 rounded-lg font-semibold text-lg flex items-center justify-center gap-2 hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Wand2 className="w-5 h-5" />
                Generate Image
              </>
            )}
          </button>

          {/* Error Display */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}
        </div>

        {/* Right Column - Output */}
        <div>
          <h2 className="text-2xl font-bold mb-6 text-gray-900">Generated Image</h2>

          <div className="border-2 border-gray-200 rounded-lg p-6 min-h-[400px] flex items-center justify-center bg-gray-50">
            {isGenerating ? (
              <div className="text-center">
                <Loader2 className="w-16 h-16 text-blue-500 animate-spin mx-auto mb-4" />
                <p className="text-gray-700 font-medium">{progressMessage}</p>
                <div className="w-64 bg-gray-200 rounded-full h-2 mt-4">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <p className="text-sm text-gray-500 mt-2">{progress}%</p>
              </div>
            ) : generatedImage ? (
              <div className="w-full">
                <img
                  src={generatedImage}
                  alt="Generated"
                  className="w-full rounded-lg shadow-lg"
                />
                <div className="flex gap-3 mt-4">
                  <button
                    onClick={handleDownload}
                    className="flex-1 bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 hover:bg-blue-700 transition-colors"
                  >
                    <Download className="w-5 h-5" />
                    Download
                  </button>
                  <button
                    onClick={handleReset}
                    className="flex-1 bg-gray-200 text-gray-700 py-3 px-4 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
                  >
                    New Image
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center">
                <ImageIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">Your generated image will appear here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImageGenerator;
