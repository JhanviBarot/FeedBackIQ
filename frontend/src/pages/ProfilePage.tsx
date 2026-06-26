import { useState, FormEvent, KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, X, Building2, Briefcase, FileText, AlertCircle, CheckCircle, Sparkles } from 'lucide-react';
import AppLayout from '../components/AppLayout';

const INDUSTRIES = [
  'Technology', 'Healthcare', 'Finance', 'Retail', 'Education',
  'Manufacturing', 'Hospitality', 'Transportation', 'Real Estate', 'Other',
];

export default function ProfilePage() {
  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('');
  const [categories, setCategories] = useState<string[]>([]);
  const [categoryInput, setCategoryInput] = useState('');
  const [description, setDescription] = useState('');
  const [urgencyDefinition, setUrgencyDefinition] = useState('');
  const [saveProfile, setSaveProfile] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState(1);
  const navigate = useNavigate();

  const handleAddCategory = () => {
    const trimmed = categoryInput.trim();
    if (trimmed && !categories.includes(trimmed) && categories.length < 8) {
      setCategories([...categories, trimmed]);
      setCategoryInput('');
    }
  };

  const handleCategoryKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddCategory();
    }
  };

  const handleRemoveCategory = (cat: string) => {
    setCategories(categories.filter((c) => c !== cat));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (step === 1 && companyName && industry) {
      setStep(2);
      return;
    }

    if (categories.length < 2) return;

    setSubmitting(true);
    await new Promise((resolve) => setTimeout(resolve, 500));

    const mockSessionId = 'session_' + Date.now();
    navigate(`/analyse/upload?session=${mockSessionId}`);
  };

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto">
        {/* Progress indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            {[1, 2].map((s) => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all ${
                    step >= s
                      ? 'gradient-bg text-white shadow-lg'
                      : 'bg-gray-200 text-muted'
                  }`}
                >
                  {step > s ? <CheckCircle className="w-5 h-5" /> : s}
                </div>
                {s < 2 && (
                  <div className={`w-16 h-1 rounded transition-all ${step > s ? 'gradient-bg' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-center gap-16 text-sm text-muted">
            <span className={step >= 1 ? 'text-primary font-medium' : ''}>Company Details</span>
            <span className={step >= 2 ? 'text-primary font-medium' : ''}>Analysis Settings</span>
          </div>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-3xl border border-gray-100 shadow-xl overflow-hidden">
          {step === 1 && (
            <div className="p-8 relative">
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-cyan-400" />
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
                  <Building2 className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Company Details</h2>
                  <p className="text-muted text-sm">Tell us about your business</p>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Company Name *</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    required
                    className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all"
                    placeholder="Acme Corp"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Briefcase className="w-4 h-4 inline mr-1" />
                    Industry *
                  </label>
                  <select
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    required
                    className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 bg-white transition-all"
                  >
                    <option value="">Select an industry</option>
                    {INDUSTRIES.map((ind) => (
                      <option key={ind} value={ind}>{ind}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <FileText className="w-4 h-4 inline mr-1" />
                    Description <span className="text-muted">(optional)</span>
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                    className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 resize-none transition-all"
                    placeholder="Brief description of your company/product..."
                  />
                </div>
              </form>

              <div className="mt-8 flex justify-end">
                <button
                  onClick={() => companyName && industry && setStep(2)}
                  className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-6 py-3.5 shadow-lg hover:shadow-xl transition-all hover:scale-[1.02]"
                >
                  Continue
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="p-8 relative">
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 to-pink-400" />
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Analysis Settings</h2>
                  <p className="text-muted text-sm">Configure what to analyze</p>
                </div>
              </div>

              <form onSubmit={handleSubmit}>
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Categories * <span className="text-muted text-xs">(2-8)</span>
                    </label>
                    <p className="text-muted text-xs mb-3">Examples: Product Quality, Customer Service, Pricing, Shipping</p>
                    <div className="flex gap-2 mb-3">
                      <input
                        type="text"
                        value={categoryInput}
                        onChange={(e) => setCategoryInput(e.target.value)}
                        onKeyDown={handleCategoryKeyDown}
                        disabled={categories.length >= 8}
                        className="flex-1 border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 disabled:bg-gray-50 transition-all"
                        placeholder="Type and press Enter"
                      />
                      <button
                        type="button"
                        onClick={handleAddCategory}
                        disabled={!categoryInput.trim() || categories.length >= 8}
                        className="px-4 rounded-xl bg-primary/10 text-primary hover:bg-primary hover:text-white transition-all disabled:opacity-50"
                      >
                        Add
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {categories.map((cat) => (
                        <span
                          key={cat}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 gradient-bg-light text-primary rounded-xl text-sm font-medium border border-primary/20"
                        >
                          {cat}
                          <button type="button" onClick={() => handleRemoveCategory(cat)} className="hover:text-red-500">
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </span>
                      ))}
                    </div>
                    {categories.length < 2 && (
                      <p className="text-xs text-amber-600 mt-2">
                        Add at least {2 - categories.length} more categories
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <AlertCircle className="w-4 h-4 inline mr-1" />
                      Urgency Definition <span className="text-muted">(optional)</span>
                    </label>
                    <textarea
                      value={urgencyDefinition}
                      onChange={(e) => setUrgencyDefinition(e.target.value)}
                      rows={2}
                      className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 resize-none transition-all"
                      placeholder="What defines an urgent issue in your context..."
                    />
                  </div>
                </div>

                <div className="mt-6 bg-gray-50 rounded-xl p-4">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={saveProfile}
                      onChange={(e) => setSaveProfile(e.target.checked)}
                      className="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                    <div>
                      <span className="text-sm font-medium text-gray-700">Save this profile for next time</span>
                      <p className="text-xs text-muted">Your settings will be pre-filled on future analyses</p>
                    </div>
                  </label>
                </div>

                <div className="mt-8 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="text-muted hover:text-gray-700 font-medium text-sm"
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    disabled={categories.length < 2 || submitting}
                    className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-6 py-3.5 shadow-lg hover:shadow-xl transition-all hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  >
                    {submitting ? 'Creating...' : 'Start Analysis'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
