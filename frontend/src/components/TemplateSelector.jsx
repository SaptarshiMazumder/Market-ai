import { useState } from 'react';
import { Upload, Eye, Loader2, Image as ImageIcon } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

const TemplateSelector = ({ productName, onTemplateReady }) => {
  const [templateUrl, setTemplateUrl] = useState('');
  const [templateFile, setTemplateFile] = useState(null);
  const [templatePreview, setTemplatePreview] = useState(null);
  const [inputMethod, setInputMethod] = useState('url');
  const [maskPreview, setMaskPreview] = useState(null);
  const [maskId, setMaskId] = useState(null);
  const [maskUrl, setMaskUrl] = useState(null);
  const [isGeneratingMask, setIsGeneratingMask] = useState(false);
  const [objectDescription, setObjectDescription] = useState('shoes, sneakers, footwear');
  const [error, setError] = useState(null);

  const normalizeObjectDescription = (value) => (value || '').trim().replace(/\s+/g, ' ');

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setTemplateFile(file);
      setTemplatePreview(URL.createObjectURL(file));
      setMaskPreview(null);
      setError(null);
    }
  };

  const getTemplateUrl = async () => {
    if (inputMethod === 'url') {
      return templateUrl;
    }
    // Upload the template image first
    const formData = new FormData();
    formData.append('image', templateFile);
    const res = await axios.post(`${API_URL}/upload-image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    // Return the served URL
    const host = window.location.protocol + '//' + 'localhost:5000';
    return `${host}/api/image-file/${res.data.filename}`;
  };

  const handlePreviewMask = async () => {
    if (inputMethod === 'url' && !templateUrl.trim()) {
      setError('Please enter a template URL');
      return;
    }
    if (inputMethod === 'upload' && !templateFile) {
      setError('Please upload a template image');
      return;
    }

    const normalizedDescription = normalizeObjectDescription(objectDescription);
    if (normalizedDescription && normalizedDescription.length < 3) {
      setError('Please enter a longer description (e.g., "headphones, headset, earphones").');
      return;
    }

    setIsGeneratingMask(true);
    setError(null);

    try {
      const url = inputMethod === 'url' ? templateUrl : await getTemplateUrl();

      const res = await axios.post(`${API_URL}/generate/mask`, {
        template_url: url,
        object_description: normalizedDescription || undefined
      });

      setMaskId(res.data.mask_id);
      setMaskUrl(res.data.mask_url);
      setMaskPreview(res.data.local_mask_url
        ? `http://localhost:5000${res.data.local_mask_url}`
        : res.data.mask_url
      );

      // Store the final template URL for inpainting
      setTemplateUrl(url);

    } catch (err) {
      console.error('Error generating mask:', err);
      const code = err.response?.data?.code;
      if (code === 'MASK_NO_DETECTIONS') {
        setError(
          `${err.response?.data?.error || 'No mask found.'} ` +
          'Try fixing spelling and using synonyms (e.g., "headphones, headset, earphones"), ' +
          'or choose a template where the product is larger/clearer.'
        );
      } else {
        setError(err.response?.data?.error || 'Failed to generate mask');
      }
    } finally {
      setIsGeneratingMask(false);
    }
  };

  const handleConfirm = () => {
    onTemplateReady({
      templateUrl: templateUrl,
      maskUrl: maskUrl,
      maskId: maskId
    });
  };

  return (
    <div>
      <h3 className="text-lg font-bold text-gray-900 mb-4">Step 3: Choose Template</h3>
      <p className="text-sm text-gray-600 mb-6">
        Upload or link a template image (e.g., a person running, walking, etc.).
        The AI will detect the product area and replace it with your trained product.
      </p>

      {/* Template Input */}
      <div className="mb-5">
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setInputMethod('url')}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
              inputMethod === 'url'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Paste Image URL
          </button>
          <button
            onClick={() => setInputMethod('upload')}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
              inputMethod === 'upload'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Upload Image
          </button>
        </div>

        {inputMethod === 'url' ? (
          <div>
            <input
              type="url"
              value={templateUrl}
              onChange={(e) => { setTemplateUrl(e.target.value); setMaskPreview(null); }}
              placeholder="https://example.com/person-running.jpg"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Use a lifestyle/action image where someone is wearing or using the product type
            </p>
          </div>
        ) : (
          <div className={`border-2 border-dashed rounded-lg p-6 text-center transition-all ${
            templatePreview ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
          }`}>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
              id="template-upload"
            />
            <label htmlFor="template-upload" className="cursor-pointer block">
              {templatePreview ? (
                <div>
                  <img src={templatePreview} alt="Template" className="max-h-40 mx-auto rounded-lg mb-2" />
                  <p className="text-sm text-blue-600 font-medium">Click to change</p>
                </div>
              ) : (
                <div>
                  <ImageIcon className="w-10 h-10 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-700 font-medium">Upload template image</p>
                  <p className="text-xs text-gray-500 mt-1">PNG, JPG, or JPEG</p>
                </div>
              )}
            </label>
          </div>
        )}
      </div>

      {/* Object Description for Masking */}
      <div className="mb-5">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          What to detect in the template
        </label>
        <input
          type="text"
          value={objectDescription}
          onChange={(e) => setObjectDescription(e.target.value)}
          placeholder="shoes, sneakers, footwear"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1">
          Describe what the AI should find and replace (e.g., "shoes", "watch", "bag", "headphones, headset, earphones")
        </p>
      </div>

      {/* Preview Mask Button */}
      <button
        onClick={handlePreviewMask}
        disabled={isGeneratingMask}
        className="w-full bg-gray-800 text-white py-3 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 hover:bg-gray-900 transition-all disabled:opacity-50 mb-6"
      >
        {isGeneratingMask ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Detecting product area...
          </>
        ) : (
          <>
            <Eye className="w-5 h-5" />
            Preview Mask
          </>
        )}
      </button>

      {/* Mask Preview */}
      {maskPreview && (
        <div className="mb-6">
          <p className="text-sm font-semibold text-gray-700 mb-2">Detected Mask:</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 mb-1">Template</p>
              <img
                src={inputMethod === 'url' ? templateUrl : templatePreview}
                alt="Template"
                className="w-full rounded-lg border border-gray-200"
              />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Mask (white = replace area)</p>
              <img
                src={maskPreview}
                alt="Mask"
                className="w-full rounded-lg border border-gray-200"
              />
            </div>
          </div>

          {/* Confirm Button */}
          <button
            onClick={handleConfirm}
            className="w-full mt-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white py-4 px-6 rounded-lg font-semibold text-lg flex items-center justify-center gap-2 hover:from-green-600 hover:to-emerald-700 transition-all"
          >
            Looks Good - Generate Image
          </button>

          <button
            onClick={handlePreviewMask}
            className="w-full mt-2 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg text-sm hover:bg-gray-200 transition-all"
          >
            Re-generate Mask
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}
    </div>
  );
};

export default TemplateSelector;
