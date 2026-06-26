import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, CheckCircle2, Zap, Sparkles, AlertCircle } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import api from '../api/client';
import type { DashboardResponse } from '../types/api';

const PROCESSING_STEPS = [
  'Parsing reviews',
  'Removing duplicates',
  'Analyzing sentiment',
  'Detecting emotions',
  'Categorizing feedback',
  'Identifying issues',
  'Generating insights',
];

export default function ProcessingPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session');
  const navigate = useNavigate();

  const [progress, setProgress] = useState(0);
  const [classifiedCount, setClassifiedCount] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [pollError, setPollError] = useState<string | null>(null);

  const stoppedRef = useRef(false);
  const failCountRef = useRef(0);
  const progressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stepIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!sessionId) {
      navigate('/dashboard');
      return;
    }

    stoppedRef.current = false;
    failCountRef.current = 0;

    // Fake progress bar fills 0→95% while polling; jumps to 100 on completion
    progressIntervalRef.current = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) return prev;
        return Math.min(prev + Math.random() * 2 + 0.3, 95);
      });
    }, 200);

    // Decorative step cycling (purely visual)
    stepIntervalRef.current = setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % PROCESSING_STEPS.length);
    }, 2500);

    // Real polling
    const poll = async () => {
      if (stoppedRef.current) return;
      try {
        const { data } = await api.get<DashboardResponse>(`/dashboard/${sessionId}`);
        failCountRef.current = 0;
        setClassifiedCount(data.total_classified);
        if (data.classification_done) {
          if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
          if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);
          setProgress(100);
          setCurrentStep(PROCESSING_STEPS.length - 1);
          setIsComplete(true);
          setTimeout(() => {
            if (!stoppedRef.current) navigate(`/results?session=${sessionId}`);
          }, 1500);
          return;
        }
      } catch {
        failCountRef.current += 1;
        if (failCountRef.current >= 3) {
          if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
          if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);
          setPollError('Analysis encountered an error. Please go back and try again.');
          return;
        }
      }
      if (!stoppedRef.current) setTimeout(poll, 3000);
    };

    // Start first poll after a short delay
    const initialTimeout = setTimeout(poll, 2000);

    return () => {
      stoppedRef.current = true;
      clearTimeout(initialTimeout);
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
      if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);
    };
  }, [sessionId, navigate]);

  if (!sessionId) return null;

  if (pollError) {
    return (
      <AppLayout>
        <div className="max-w-lg mx-auto py-12">
          <div className="bg-white rounded-3xl border border-gray-100 shadow-xl p-8 text-center">
            <div className="w-20 h-20 rounded-2xl bg-red-100 flex items-center justify-center mx-auto mb-6">
              <AlertCircle className="w-10 h-10 text-red-500" />
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">Analysis Failed</h1>
            <p className="text-muted mb-6">{pollError}</p>
            <button
              onClick={() => navigate('/dashboard')}
              className="gradient-bg text-white font-semibold rounded-xl px-6 py-3"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-lg mx-auto py-12">
        <div className="bg-white rounded-3xl border border-gray-100 shadow-xl p-8 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 gradient-bg" />

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

          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {isComplete ? 'Analysis Complete!' : 'Analyzing Your Reviews'}
            </h1>
            <p className="text-muted">
              {isComplete ? 'Redirecting to results...' : 'Our AI is processing your feedback'}
            </p>
          </div>

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
              <span className="text-muted">{isComplete ? 'Done' : PROCESSING_STEPS[currentStep]}</span>
              <span className="text-primary font-medium">{currentStep + 1}/{PROCESSING_STEPS.length}</span>
            </div>
          </div>

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

          <div className="bg-gray-50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-primary" />
              <span className="text-xs font-medium text-muted uppercase tracking-wider">Processing Steps</span>
            </div>
            <div className="space-y-1">
              {PROCESSING_STEPS.map((step, index) => (
                <div
                  key={step}
                  className={`flex items-center gap-3 py-1.5 px-2 rounded-lg transition-colors ${
                    isComplete
                      ? 'bg-green-50 text-green-600'
                      : index < currentStep
                      ? 'bg-green-50 text-green-600'
                      : index === currentStep
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted'
                  }`}
                >
                  {(isComplete || index < currentStep) ? (
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  ) : index === currentStep ? (
                    <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin" />
                  ) : (
                    <div className="w-4 h-4 flex-shrink-0 rounded-full border border-current" />
                  )}
                  <span className="text-sm">{step}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
