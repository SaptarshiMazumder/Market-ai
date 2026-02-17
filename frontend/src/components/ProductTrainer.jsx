import { useState } from 'react';
import { Upload, Package, Loader2, CheckCircle, Link } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

const ProductTrainer = ({ onTrainingStarted, onTrainingImported }) => {
  const [productName, setProductName] = useState('');
  const [inputMethod, setInputMethod] = useState('upload'); // 'upload' or 'url'
  const [zipFile, setZipFile] = useState(null);
  const [zipUrl, setZipUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState('');
  const [importMethod, setImportMethod] = useState('manual'); // 'manual' or 'json'
  const [importVersionId, setImportVersionId] = useState('');
  const [importTriggerWord, setImportTriggerWord] = useState('');
  const [importTrainingId, setImportTrainingId] = useState('');
  const [replicatePayloadText, setReplicatePayloadText] = useState('');
  const [importStatus, setImportStatus] = useState('');

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.name.endsWith('.zip')) {
      setZipFile(file);
      setError(null);
    } else {
      setError('Please select a ZIP file');
    }
  };

  const handleSubmit = async () => {
    if (!productName.trim()) {
      setError('Please enter a product name');
      return;
    }
    if (inputMethod === 'upload' && !zipFile) {
      setError('Please upload a ZIP file with training images');
      return;
    }
    if (inputMethod === 'url' && !zipUrl.trim()) {
      setError('Please enter a URL to the training ZIP file');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // Step 1: Register the product
      setStatus('Registering product on Replicate...');
      await axios.post(`${API_URL}/products/register`, {
        product_name: productName.trim()
      });

      // Step 2: Upload ZIP if needed
      let finalZipUrl = zipUrl;
      if (inputMethod === 'upload') {
        setStatus('Uploading training data...');
        const formData = new FormData();
        formData.append('file', zipFile);
        const uploadRes = await axios.post(
          `${API_URL}/products/upload-training-data`,
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        );
        // Use the uploaded file reference
        finalZipUrl = null; // We'll use uploaded_file instead
        var uploadedFile = uploadRes.data.filename;
      }

      // Step 3: Start training
      setStatus('Starting LoRA training...');
      const trainPayload = { product_name: productName.trim() };
      if (finalZipUrl) {
        trainPayload.zip_url = finalZipUrl;
      } else {
        trainPayload.uploaded_file = uploadedFile;
      }

      const trainRes = await axios.post(`${API_URL}/products/train`, trainPayload);

      // Training started successfully
      onTrainingStarted({
        productName: productName.trim(),
        trainingId: trainRes.data.training_id,
        triggerWord: trainRes.data.trigger_word
      });

    } catch (err) {
      console.error('Error:', err);
      setError(err.response?.data?.error || 'Failed to start training');
      setIsSubmitting(false);
      setStatus('');
    }
  };

  const handleImport = async () => {
    if (!productName.trim()) {
      setError('Please enter a product name');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setImportStatus('Importing trained model...');

    try {
      let payload = { product_name: productName.trim() };

      if (importMethod === 'json') {
        if (!replicatePayloadText.trim()) {
          setError('Please paste the Replicate JSON payload');
          setIsSubmitting(false);
          setImportStatus('');
          return;
        }
        let parsed;
        try {
          parsed = JSON.parse(replicatePayloadText);
        } catch (e) {
          setError('Invalid JSON. Please paste the full Replicate response JSON.');
          setIsSubmitting(false);
          setImportStatus('');
          return;
        }
        payload.replicate_payload = parsed;
      } else {
        if (!importVersionId.trim() || !importTriggerWord.trim()) {
          setError('Please provide both version ID and trigger word');
          setIsSubmitting(false);
          setImportStatus('');
          return;
        }
        payload.version_id = importVersionId.trim();
        payload.trigger_word = importTriggerWord.trim();
        if (importTrainingId.trim()) {
          payload.training_id = importTrainingId.trim();
        }
      }

      await axios.post(`${API_URL}/products/import-trained`, payload);

      if (onTrainingImported) {
        onTrainingImported({ productName: productName.trim() });
      }
    } catch (err) {
      console.error('Error:', err);
      setError(err.response?.data?.error || 'Failed to import trained model');
      setIsSubmitting(false);
      setImportStatus('');
    }
  };

  return (
    <div>
      <h3 className="text-lg font-bold text-gray-900 mb-4">Step 1: Train Your Product</h3>
      <p className="text-sm text-gray-600 mb-6">
        Upload 10-20 high-quality images of your product in a ZIP file.
        Include different angles: front, side, top-down, and 45-degree.
        Images should be 1024x1024 for best results.
      </p>

      {/* Product Name */}
      <div className="mb-5">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Product Name *
        </label>
        <input
          type="text"
          value={productName}
          onChange={(e) => setProductName(e.target.value)}
          placeholder="e.g., Nike Air Max 90, Apple Watch Ultra..."
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          disabled={isSubmitting}
        />
        <p className="text-xs text-gray-500 mt-1">
          This becomes the Product ID on Replicate
        </p>
      </div>

      {/* Input Method Toggle */}
      <div className="mb-5">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Training Images
        </label>
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setInputMethod('upload')}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
              inputMethod === 'upload'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            disabled={isSubmitting}
          >
            <Upload className="w-4 h-4 inline mr-1" />
            Upload ZIP
          </button>
          <button
            onClick={() => setInputMethod('url')}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
              inputMethod === 'url'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            disabled={isSubmitting}
          >
            <Link className="w-4 h-4 inline mr-1" />
            Paste URL
          </button>
        </div>

        {inputMethod === 'upload' ? (
          <div className={`border-2 border-dashed rounded-lg p-6 text-center transition-all ${
            zipFile ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-blue-400'
          }`}>
            <input
              type="file"
              accept=".zip"
              onChange={handleFileSelect}
              className="hidden"
              id="zip-upload"
              disabled={isSubmitting}
            />
            <label htmlFor="zip-upload" className="cursor-pointer block">
              {zipFile ? (
                <div>
                  <CheckCircle className="w-10 h-10 text-green-500 mx-auto mb-2" />
                  <p className="text-sm font-medium text-green-700">{zipFile.name}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {(zipFile.size / 1024 / 1024).toFixed(1)} MB - Click to change
                  </p>
                </div>
              ) : (
                <div>
                  <Package className="w-10 h-10 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-gray-700">Drop your ZIP file here</p>
                  <p className="text-xs text-gray-500 mt-1">
                    10-20 product images, 1024x1024 recommended
                  </p>
                </div>
              )}
            </label>
          </div>
        ) : (
          <div>
            <input
              type="url"
              value={zipUrl}
              onChange={(e) => setZipUrl(e.target.value)}
              placeholder="https://example.com/my-product-images.zip"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">
              Must be a publicly accessible URL to a ZIP file
            </p>
          </div>
        )}
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={isSubmitting || !productName.trim()}
        className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 px-6 rounded-lg font-semibold text-lg flex items-center justify-center gap-2 hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            {status}
          </>
        ) : (
          <>
            <Package className="w-5 h-5" />
            Start Training
          </>
        )}
      </button>

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* Info Box */}
      <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
        <p className="text-sm font-semibold text-amber-800 mb-2">Training Tips:</p>
        <ul className="text-xs text-amber-700 space-y-1 list-disc list-inside">
          <li>Use 10-20 high-resolution images of the same product</li>
          <li>Include diverse angles: side, front, top-down, 45-degree</li>
          <li>Clean backgrounds work best for training</li>
          <li>Training takes approximately 15-30 minutes</li>
          <li>Cost: ~$2-3 per training run on Replicate</li>
        </ul>
      </div>

      {/* Import Trained Model */}
      <div className="mt-8 border-t border-gray-200 pt-6">
        <h4 className="text-md font-bold text-gray-900 mb-2">Already Trained?</h4>
        <p className="text-sm text-gray-600 mb-4">
          Import a completed Replicate training and skip the wait step.
        </p>

        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setImportMethod('manual')}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
              importMethod === 'manual'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            disabled={isSubmitting}
          >
            Manual Entry
          </button>
          <button
            onClick={() => setImportMethod('json')}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
              importMethod === 'json'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            disabled={isSubmitting}
          >
            Paste JSON
          </button>
        </div>

        {importMethod === 'manual' ? (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">
                Replicate Version ID *
              </label>
              <input
                type="text"
                value={importVersionId}
                onChange={(e) => setImportVersionId(e.target.value)}
                placeholder="owner/model:version_hash"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={isSubmitting}
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">
                Trigger Word *
              </label>
              <input
                type="text"
                value={importTriggerWord}
                onChange={(e) => setImportTriggerWord(e.target.value)}
                placeholder="TOK_MYPRODUCT"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={isSubmitting}
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">
                Training ID (optional)
              </label>
              <input
                type="text"
                value={importTrainingId}
                onChange={(e) => setImportTrainingId(e.target.value)}
                placeholder="j47n067ay1rmw0cwba8va9csy4"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={isSubmitting}
              />
            </div>
          </div>
        ) : (
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              Replicate Training JSON *
            </label>
            <textarea
              value={replicatePayloadText}
              onChange={(e) => setReplicatePayloadText(e.target.value)}
              placeholder="Paste the full Replicate response JSON here"
              className="w-full h-40 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-xs"
              disabled={isSubmitting}
            />
          </div>
        )}

        <button
          onClick={handleImport}
          disabled={isSubmitting || !productName.trim()}
          className="w-full mt-4 bg-gray-900 text-white py-3 px-6 rounded-lg font-semibold text-base flex items-center justify-center gap-2 hover:bg-black transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              {importStatus || 'Importing...'}
            </>
          ) : (
            <>
              <CheckCircle className="w-5 h-5" />
              Import Trained Model
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default ProductTrainer;
