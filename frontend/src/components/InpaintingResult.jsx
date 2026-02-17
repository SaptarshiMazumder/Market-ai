import { useState, useEffect } from 'react';
import { Download, RefreshCw, Loader2, CheckCircle } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

const InpaintingResult = ({ templateUrl, maskUrl, productName, onReset, onNewTemplate }) => {
  const [isGenerating, setIsGenerating] = useState(true);
  const [resultImage, setResultImage] = useState(null);
  const [resultId, setResultId] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    generateImage();
  }, []);

  const generateImage = async () => {
    setIsGenerating(true);
    setError(null);

    try {
      const res = await axios.post(`${API_URL}/generate/inpaint`, {
        template_url: templateUrl,
        mask_url: maskUrl,
        product_name: productName,
        product_description: productName
      });

      setResultId(res.data.result_id);
      setResultImage(`http://localhost:5000${res.data.image_url}`);
    } catch (err) {
      console.error('Inpainting error:', err);
      setError(err.response?.data?.error || 'Failed to generate image');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (resultId) {
      window.open(`${API_URL}/generate/download/${resultId}`, '_blank');
    }
  };

  return (
    <div>
      <h3 className="text-lg font-bold text-gray-900 mb-4">Step 4: Your Product Image</h3>

      {isGenerating ? (
        <div className="bg-gray-50 rounded-xl p-12 text-center">
          <Loader2 className="w-16 h-16 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-lg font-semibold text-gray-700">Generating your image...</p>
          <p className="text-sm text-gray-500 mt-2">
            Inpainting your trained product into the template. This takes about 30-60 seconds.
          </p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <p className="text-red-700 font-semibold mb-2">Generation Failed</p>
          <p className="text-red-600 text-sm">{error}</p>
          <button
            onClick={generateImage}
            className="mt-4 bg-red-100 text-red-700 py-2 px-4 rounded-lg text-sm font-medium hover:bg-red-200 transition-all"
          >
            Try Again
          </button>
        </div>
      ) : (
        <div>
          {/* Success Banner */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <p className="text-green-700 text-sm font-medium">Image generated successfully!</p>
          </div>

          {/* Before/After Comparison */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <p className="text-xs font-semibold text-gray-500 mb-1 uppercase">Template (Before)</p>
              <img
                src={templateUrl}
                alt="Template"
                className="w-full rounded-lg border border-gray-200 shadow-sm"
              />
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-500 mb-1 uppercase">Result (After)</p>
              <img
                src={resultImage}
                alt="Result"
                className="w-full rounded-lg border border-gray-200 shadow-sm"
              />
            </div>
          </div>

          {/* Full Result */}
          <div className="mb-6">
            <p className="text-xs font-semibold text-gray-500 mb-1 uppercase">Full Result</p>
            <img
              src={resultImage}
              alt="Full Result"
              className="w-full rounded-xl shadow-lg"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleDownload}
              className="flex-1 bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 hover:bg-blue-700 transition-colors"
            >
              <Download className="w-5 h-5" />
              Download
            </button>
            <button
              onClick={onNewTemplate}
              className="flex-1 bg-gray-200 text-gray-700 py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 hover:bg-gray-300 transition-colors"
            >
              <RefreshCw className="w-5 h-5" />
              Try Another Template
            </button>
          </div>

          <button
            onClick={onReset}
            className="w-full mt-3 bg-gray-100 text-gray-600 py-2 px-4 rounded-lg text-sm hover:bg-gray-200 transition-all"
          >
            Start Over with New Product
          </button>
        </div>
      )}
    </div>
  );
};

export default InpaintingResult;
