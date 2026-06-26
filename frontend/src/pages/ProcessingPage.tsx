import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, CheckCircle2, Zap, Sparkles } from 'lucide-react';
import AppLayout from '../components/AppLayout';

const PROCESSING_STEPS = [
  { label: 'Parsing reviews', duration: 2000 },
  { label: 'Removing duplicates', duration: 1500 },
  { label: 'Analyzing sentiment', duration: 3000 },
  { label: 'Detecting emotions', duration: 2500 },
  { label: 'Categorizing feedback', duration: 2000 },
  { label: 'Identifying issues', duration: 1500 },
  { label: 'Generating insights', duration: 2000 },
];

export default function ProcessingPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session');
  const navigate = useNavigate();

  const [progress, setProgress] = useState(0);
  const [classifiedCount, setClassifiedCount] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const progressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stepIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!sessionId) {
      navigate('/dashboard');
      return;
    }

    progressIntervalRef.current = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) return prev;
        const increment = Math.random() * 2 + 0.5;
        return Math.min(prev + increment, 95);
      });
    }, 150);

    let stepIndex = 0;
    const runStep = () => {
      if (stepIndex < PROCESSING_STEPS.length) {
        setCurrentStep(stepIndex);
        stepIndex++;
        stepIntervalRef.current = setTimeout(runStep, PROCESSING_STEPS[stepIndex - 1].duration);
      } else {
        setProgress(100);
        setIsComplete(true);
        setTimeout(() => {
          navigate(`/results?session=${sessionId}`);
        }, 1500);
      }
    };
    stepIntervalRef.current = setTimeout(runStep, 500);

    countIntervalRef.current = setInterval(() => {
      setClassifiedCount((prev) => {
        const increment = Math.floor(Math.random() * 15) + 5;
        return prev + increment;
      });
    }, 200);

    return () => {
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
      if (stepIntervalRef.current) clearTimeout(stepIntervalRef.current);
      if (countIntervalRef.current) clearInterval(countIntervalRef.current);
    };
  }, [sessionId, navigate]);

  if (!sessionId) return null;

  return (
    <AppLayout>
      <div className="max-w-lg mx-auto py-12">
        <div className="bg-white rounded-3xl border border-gray-100 shadow-xl p-8 relative overflow-hidden">
          {/* Top gradient bar */}
          <div className="absolute top-0 left-0 right-0 h-1 gradient-bg" />

          {/* Icon */}
          <div className="flex justify-center mb-6">
            {isComplete ? (
              <div className="w-20 h-20 rounded-2xl bg-green-100 flex items-center justify-center">
                <CheckCircle2 className="w-10 h-10 text-green-500" />
              </div>
            ) : (
              <div className="w-20 h-20 rounded-2xl gradient-bg flex items-center justify-center shadow-lg pulse-glow">
                <Sparkles className="w-10 h-10 text-white animate-pulse" />
              </div>
            )}
          </div>

          {/* Title */}
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {isComplete ? 'Analysis Complete!' : 'Analyzing Your Reviews'}
            </h1>
            <p className="text-muted">
              {isComplete ? 'Redirecting to results...' : 'Our AI is processing your feedback'}
            </p>
          </div>

          {/* Progress bar */}
          <div className="mb-8">
            <div className="relative h-4 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 gradient-bg rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-bold text-gray-700">{Math.round(progress)}%</span>
              </div>
            </div>
            <div className="flex justify-between mt-2 text-sm">
              <span className="text-muted">{isComplete ? 'Done' : PROCESSING_STEPS[currentStep]?.label}</span>
              <span className="text-primary font-medium">{currentStep + 1}/{PROCESSING_STEPS.length}</span>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-4 text-center">
              <p className="text-3xl font-bold gradient-text">{classifiedCount.toLocaleString()}</p>
              <p className="text-xs text-muted mt-1">Reviews processed</p>
            </div>
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-4 text-center">
              <p className="text-3xl font-bold text-gray-700">{currentStep + 1}/{PROCESSING_STEPS.length}</p>
              <p className="text-xs text-muted mt-1">Steps completed</p>
            </div>
          </div>

          {/* Steps */}
          <div className="bg-gray-50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-primary" />
              <span className="text-xs font-medium text-muted uppercase tracking-wider">Processing Steps</span>
            </div>
            <div className="space-y-1">
              {PROCESSING_STEPS.map((step, index) => (
                <div
                  key={step.label}
                  className={`flex items-center gap-3 py-1.5 px-2 rounded-lg transition-colors ${
                    index < currentStep
                      ? 'bg-green-50 text-green-600'
                      : index === currentStep
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted'
                  }`}
                >
                  {index < currentStep ? (
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  ) : index === currentStep ? (
                    <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin" />
                  ) : (
                    <div className="w-4 h-4 flex-shrink-0 rounded-full border border-current" />
                  )}
                  <span className="text-sm">{step.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
