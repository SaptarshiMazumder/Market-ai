import { useState, useEffect } from 'react';
import { Layers, Play, Loader2, Download, CheckCircle, XCircle, Image as ImageIcon } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

const BatchProcessor = () => {
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [templateUrls, setTemplateUrls] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [batchJobId, setBatchJobId] = useState(null);
  const [batchStatus, setBatchStatus] = useState(null);
  const [error, setError] = useState(null);

  // Load trained products on mount
  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const res = await axios.get(`${API_URL}/products/trained`);
      setProducts(res.data.products || []);
    } catch (err) {
      console.error('Error loading products:', err);
    }
  };

  // Poll batch status
  useEffect(() => {
    if (!batchJobId) return;

    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_URL}/batch/status/${batchJobId}`);
        setBatchStatus(res.data);

        if (res.data.job?.status === 'completed') {
          clearInterval(interval);
          setIsProcessing(false);
        }
      } catch (err) {
        console.error('Error polling batch status:', err);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [batchJobId]);

  const handleStart = async () => {
    if (!selectedProduct) {
      setError('Please select a trained product');
      return;
    }

    const urls = templateUrls
      .split('\n')
      .map(u => u.trim())
      .filter(u => u.length > 0);

    if (urls.length === 0) {
      setError('Please enter at least one template URL');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setBatchStatus(null);

    try {
      const res = await axios.post(`${API_URL}/batch/start`, {
        product_name: selectedProduct,
        template_urls: urls
      });

      setBatchJobId(res.data.batch_job_id);
    } catch (err) {
      console.error('Error starting batch:', err);
      setError(err.response?.data?.error || 'Failed to start batch processing');
      setIsProcessing(false);
    }
  };

  const getItemStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'masking':
      case 'inpainting':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <div className="w-5 h-5 rounded-full bg-gray-200" />;
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Batch Processing</h2>
      <p className="text-gray-600 mb-6">
        Process multiple template images with a trained product in one go.
      </p>

      {/* Product Selection */}
      <div className="mb-5">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Trained Product *
        </label>
        {products.length === 0 ? (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <p className="text-amber-700 text-sm">
              No trained products found. Go to the "Product Pipeline" tab to train a product first.
            </p>
          </div>
        ) : (
          <select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isProcessing}
          >
            <option value="">Select a product...</option>
            {products.map((p) => (
              <option key={p.product_name} value={p.product_name}>
                {p.product_name} ({p.trigger_word})
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Template URLs */}
      <div className="mb-5">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Template Image URLs * (one per line)
        </label>
        <textarea
          value={templateUrls}
          onChange={(e) => setTemplateUrls(e.target.value)}
          placeholder={"https://example.com/person-running-1.jpg\nhttps://example.com/person-walking-2.jpg\nhttps://example.com/lifestyle-3.jpg"}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none font-mono text-sm"
          rows="5"
          disabled={isProcessing}
        />
        <p className="text-xs text-gray-500 mt-1">
          Enter publicly accessible image URLs, one per line
        </p>
      </div>

      {/* Start Button */}
      <button
        onClick={handleStart}
        disabled={isProcessing || products.length === 0}
        className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 px-6 rounded-lg font-semibold text-lg flex items-center justify-center gap-2 hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed mb-6"
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            Start Batch Processing
          </>
        )}
      </button>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* Batch Results */}
      {batchStatus && (
        <div>
          {/* Overall Progress */}
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <div className="flex justify-between text-sm mb-2">
              <span className="font-semibold text-gray-700">Overall Progress</span>
              <span className="text-gray-500">
                {batchStatus.job?.completed_items || 0} / {batchStatus.job?.total_items || 0}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="bg-blue-500 h-3 rounded-full transition-all duration-500"
                style={{
                  width: `${batchStatus.job?.total_items
                    ? (batchStatus.job.completed_items / batchStatus.job.total_items) * 100
                    : 0}%`
                }}
              />
            </div>
          </div>

          {/* Per-Item Status */}
          <div className="space-y-3">
            {(batchStatus.items || []).map((item, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg"
              >
                {getItemStatusIcon(item.status)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-700 truncate">
                    Template {idx + 1}
                  </p>
                  <p className="text-xs text-gray-500 capitalize">{item.status}</p>
                  {item.error && (
                    <p className="text-xs text-red-500 mt-1">{item.error}</p>
                  )}
                </div>
                {item.image_url && (
                  <div className="flex gap-2">
                    <a
                      href={`http://localhost:5000${item.image_url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-all"
                    >
                      <ImageIcon className="w-4 h-4 text-gray-600" />
                    </a>
                    <a
                      href={`http://localhost:5000${item.image_url}`}
                      download
                      className="p-2 bg-blue-100 rounded-lg hover:bg-blue-200 transition-all"
                    >
                      <Download className="w-4 h-4 text-blue-600" />
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BatchProcessor;
