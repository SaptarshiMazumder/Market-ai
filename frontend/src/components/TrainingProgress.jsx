import { useState, useEffect } from 'react';
import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

const TrainingProgress = ({ trainingId, productName, triggerWord, onTrainingComplete }) => {
  const [status, setStatus] = useState('starting');
  const [logs, setLogs] = useState('');
  const [versionId, setVersionId] = useState(null);
  const [error, setError] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!trainingId) return;

    const pollInterval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_URL}/products/train-status/${trainingId}`);
        const data = res.data;

        setStatus(data.status);
        if (data.logs) setLogs(data.logs);

        if (data.status === 'succeeded') {
          setVersionId(data.version_id);
          clearInterval(pollInterval);
          onTrainingComplete({
            versionId: data.version_id,
            productName,
            triggerWord
          });
        } else if (data.status === 'failed' || data.status === 'canceled') {
          clearInterval(pollInterval);
          setError(data.error || 'Training failed');
        }
      } catch (err) {
        console.error('Error polling training status:', err);
      }
    }, 10000); // Poll every 10 seconds

    // Initial poll
    (async () => {
      try {
        const res = await axios.get(`${API_URL}/products/train-status/${trainingId}`);
        setStatus(res.data.status);
        if (res.data.logs) setLogs(res.data.logs);
      } catch (err) {
        console.error('Initial poll error:', err);
      }
    })();

    return () => clearInterval(pollInterval);
  }, [trainingId]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'succeeded':
        return <CheckCircle className="w-12 h-12 text-green-500" />;
      case 'failed':
      case 'canceled':
        return <XCircle className="w-12 h-12 text-red-500" />;
      default:
        return <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'starting':
        return 'Initializing training environment...';
      case 'processing':
        return 'Training LoRA model on your product images...';
      case 'succeeded':
        return 'Training completed successfully!';
      case 'failed':
        return 'Training failed.';
      case 'canceled':
        return 'Training was canceled.';
      default:
        return 'Preparing...';
    }
  };

  const getEstimatedProgress = () => {
    if (status === 'succeeded') return 100;
    if (status === 'failed' || status === 'canceled') return 0;
    // Rough estimate: training takes ~20 minutes
    const estimated = Math.min(95, (elapsed / 1200) * 100);
    return Math.round(estimated);
  };

  return (
    <div>
      <h3 className="text-lg font-bold text-gray-900 mb-4">Step 2: Training in Progress</h3>

      {/* Status Card */}
      <div className="bg-gray-50 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-4 mb-4">
          {getStatusIcon()}
          <div>
            <p className="text-lg font-semibold text-gray-900">{getStatusText()}</p>
            <p className="text-sm text-gray-500">Product: {productName}</p>
          </div>
        </div>

        {/* Progress Bar */}
        {status !== 'failed' && status !== 'canceled' && (
          <div className="mb-4">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Progress</span>
              <span>{getEstimatedProgress()}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-1000 ${
                  status === 'succeeded' ? 'bg-green-500' : 'bg-blue-500'
                }`}
                style={{ width: `${getEstimatedProgress()}%` }}
              />
            </div>
          </div>
        )}

        {/* Timer */}
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Clock className="w-4 h-4" />
          <span>Elapsed: {formatTime(elapsed)}</span>
          {status === 'processing' && (
            <span className="text-gray-400">| Usually takes 15-30 minutes</span>
          )}
        </div>
      </div>

      {/* Training Details */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Training ID:</span>
            <p className="font-mono text-xs text-gray-700 truncate">{trainingId}</p>
          </div>
          <div>
            <span className="text-gray-500">Trigger Word:</span>
            <p className="font-semibold text-blue-600">{triggerWord}</p>
          </div>
          <div>
            <span className="text-gray-500">Status:</span>
            <p className={`font-semibold ${
              status === 'succeeded' ? 'text-green-600' :
              status === 'failed' ? 'text-red-600' : 'text-blue-600'
            }`}>
              {status}
            </p>
          </div>
          {versionId && (
            <div>
              <span className="text-gray-500">Version ID:</span>
              <p className="font-mono text-xs text-gray-700 truncate">{versionId}</p>
            </div>
          )}
        </div>
      </div>

      {/* Training Logs */}
      {logs && (
        <div className="mb-4">
          <p className="text-sm font-semibold text-gray-700 mb-2">Training Logs:</p>
          <div className="bg-gray-900 text-green-400 rounded-lg p-4 font-mono text-xs max-h-48 overflow-y-auto">
            <pre className="whitespace-pre-wrap">{logs}</pre>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* Success Message */}
      {status === 'succeeded' && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-800 font-semibold">Your product LoRA is ready!</p>
          <p className="text-green-700 text-sm mt-1">
            The AI has learned what your product looks like. You can now place it into any template image.
          </p>
        </div>
      )}
    </div>
  );
};

export default TrainingProgress;
