import { useState } from 'react';
import { CheckCircle } from 'lucide-react';
import ProductTrainer from './ProductTrainer';
import TrainingProgress from './TrainingProgress';
import TemplateSelector from './TemplateSelector';
import InpaintingResult from './InpaintingResult';

const steps = [
  { id: 1, label: 'Train' },
  { id: 2, label: 'Wait' },
  { id: 3, label: 'Template' },
  { id: 4, label: 'Generate' }
];

const ProductPipeline = () => {
  const [currentStep, setCurrentStep] = useState(1);

  // Training state
  const [trainingInfo, setTrainingInfo] = useState(null);
  const [trainedProduct, setTrainedProduct] = useState(null);

  // Template state
  const [templateInfo, setTemplateInfo] = useState(null);

  const handleTrainingStarted = (info) => {
    setTrainingInfo(info);
    setCurrentStep(2);
  };

  const handleTrainingImported = (info) => {
    setTrainingInfo(null);
    setTrainedProduct(info);
    setCurrentStep(3);
  };

  const handleTrainingComplete = (info) => {
    setTrainedProduct(info);
    setCurrentStep(3);
  };

  const handleTemplateReady = (info) => {
    setTemplateInfo(info);
    setCurrentStep(4);
  };

  const handleReset = () => {
    setCurrentStep(1);
    setTrainingInfo(null);
    setTrainedProduct(null);
    setTemplateInfo(null);
  };

  const handleNewTemplate = () => {
    setTemplateInfo(null);
    setCurrentStep(3);
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8">
      {/* Step Indicator */}
      <div className="flex items-center justify-between mb-8">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                currentStep > step.id
                  ? 'bg-green-500 text-white'
                  : currentStep === step.id
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-500'
              }`}>
                {currentStep > step.id ? (
                  <CheckCircle className="w-5 h-5" />
                ) : (
                  step.id
                )}
              </div>
              <span className={`text-sm font-medium hidden sm:inline ${
                currentStep >= step.id ? 'text-gray-900' : 'text-gray-400'
              }`}>
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div className={`w-12 sm:w-24 h-0.5 mx-2 ${
                currentStep > step.id ? 'bg-green-500' : 'bg-gray-200'
              }`} />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      {currentStep === 1 && (
        <ProductTrainer
          onTrainingStarted={handleTrainingStarted}
          onTrainingImported={handleTrainingImported}
        />
      )}

      {currentStep === 2 && trainingInfo && (
        <TrainingProgress
          trainingId={trainingInfo.trainingId}
          productName={trainingInfo.productName}
          triggerWord={trainingInfo.triggerWord}
          onTrainingComplete={handleTrainingComplete}
        />
      )}

      {currentStep === 3 && trainedProduct && (
        <TemplateSelector
          productName={trainedProduct.productName}
          onTemplateReady={handleTemplateReady}
        />
      )}

      {currentStep === 4 && templateInfo && trainedProduct && (
        <InpaintingResult
          templateUrl={templateInfo.templateUrl}
          maskUrl={templateInfo.maskUrl}
          productName={trainedProduct.productName}
          onReset={handleReset}
          onNewTemplate={handleNewTemplate}
        />
      )}
    </div>
  );
};

export default ProductPipeline;
