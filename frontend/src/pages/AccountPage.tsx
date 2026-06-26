import { useState, useEffect, FormEvent, KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Briefcase, Key, History, Save, Check, X, Mail, Calendar, BarChart3 } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import { getMe, updateProfile, changePassword } from '../api/auth';
import { listSessions } from '../api/sessions';
import type { UserMeResponse, SessionSummary } from '../types/api';

const INDUSTRIES = [
  'Technology', 'Healthcare', 'Finance', 'Retail', 'Education',
  'Manufacturing', 'Hospitality', 'Transportation', 'Real Estate', 'Other',
];

export default function AccountPage() {
  const navigate = useNavigate();
  const [meData, setMeData] = useState<UserMeResponse | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);

  // Profile form
  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('Technology');
  const [categories, setCategories] = useState<string[]>([]);
  const [categoryInput, setCategoryInput] = useState('');
  const [description, setDescription] = useState('');
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Password form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then((data) => {
        setMeData(data);
        if (data.profile) {
          setCompanyName(data.profile.company_name || '');
          setIndustry(data.profile.industry || 'Technology');
          setCategories(data.profile.categories || []);
          setDescription(data.profile.description || '');
        }
        // Update localStorage with fresh data
        const stored = localStorage.getItem('user_data');
        const existing = stored ? JSON.parse(stored) : {};
        localStorage.setItem('user_data', JSON.stringify({ ...existing, full_name: data.full_name, email: data.email }));
      })
      .catch(() => {});

    listSessions()
      .then((r) => setSessions(r.sessions))
      .catch(() => setSessions([]));
  }, []);

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

  const handleSaveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setProfileLoading(true);
    setProfileSaved(false);
    setProfileError(null);
    try {
      await updateProfile({
        company_name: companyName,
        industry,
        categories,
        description: description || null,
        urgency_definition: null,
      });
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = axiosErr?.response?.data?.detail;
      setProfileError(typeof detail === 'string' ? detail : 'Failed to save profile.');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordLoading(true);
    setPasswordSaved(false);
    setPasswordError(null);
    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters');
      setPasswordLoading(false);
      return;
    }
    try {
      await changePassword(currentPassword, newPassword);
      setPasswordSaved(true);
      setCurrentPassword('');
      setNewPassword('');
      setTimeout(() => setPasswordSaved(false), 3000);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = axiosErr?.response?.data?.detail;
      setPasswordError(typeof detail === 'string' ? detail : 'Failed to update password.');
    } finally {
      setPasswordLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-500';
    if (score >= 50) return 'text-amber-500';
    return 'text-red-500';
  };

  const displayName = meData?.full_name || 'User';
  const initials = displayName.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2);

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto">
        {/* User Info Header */}
        <div className="bg-white rounded-3xl border border-gray-100 shadow-xl p-6 mb-8 overflow-hidden relative">
          <div className="absolute top-0 left-0 right-0 h-1 gradient-bg" />
          <div className="flex items-center gap-4 relative pt-2">
            <div className="w-16 h-16 rounded-2xl gradient-bg flex items-center justify-center text-white text-xl font-bold shadow-lg">
              {initials}
            </div>
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900">{displayName}</h1>
              <div className="flex flex-wrap gap-4 text-sm text-muted mt-1">
                <span className="flex items-center gap-1"><Mail className="w-3.5 h-3.5" />{meData?.email || '—'}</span>
                {meData?.created_at && (
                  <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />Joined {formatDate(meData.created_at)}</span>
                )}
                <span className="flex items-center gap-1"><History className="w-3.5 h-3.5" />{sessions.length} analyses</span>
              </div>
            </div>
          </div>
        </div>

        {/* Panels */}
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          {/* Company Profile */}
          <div className="bg-white rounded-3xl border border-gray-100 shadow-lg p-6 overflow-hidden relative">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-blue-500 to-cyan-400" />
            <div className="flex items-center gap-3 mb-6 relative">
              <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-blue-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Company Profile</h2>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Company Name</label>
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
                  <Briefcase className="w-4 h-4 inline mr-1" />Industry
                </label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 bg-white transition-all"
                >
                  {INDUSTRIES.map((ind) => (
                    <option key={ind} value={ind}>{ind}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Categories</label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={categoryInput}
                    onChange={(e) => setCategoryInput(e.target.value)}
                    onKeyDown={handleCategoryKeyDown}
                    disabled={categories.length >= 8}
                    className="flex-1 border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 disabled:bg-gray-50 transition-all"
                    placeholder="Add category…"
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
                    <span key={cat} className="inline-flex items-center gap-1.5 px-3 py-1.5 gradient-bg-light text-primary rounded-xl text-sm font-medium border border-primary/20">
                      {cat}
                      <button type="button" onClick={() => handleRemoveCategory(cat)} className="hover:text-red-500">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 resize-none transition-all"
                  placeholder="Brief description of your company…"
                />
              </div>

              {profileError && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2">
                  <p className="text-red-500 text-sm">{profileError}</p>
                </div>
              )}

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={profileLoading || categories.length < 1}
                  className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-5 py-2.5 shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  {profileLoading ? 'Saving…' : 'Save Profile'}
                </button>
                {profileSaved && (
                  <span className="flex items-center gap-1 text-green-500 text-sm">
                    <Check className="w-4 h-4" />Profile saved.
                  </span>
                )}
              </div>
            </form>
          </div>

          {/* Change Password */}
          <div className="bg-white rounded-3xl border border-gray-100 shadow-lg p-6 overflow-hidden relative">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-purple-500 to-pink-400" />
            <div className="flex items-center gap-3 mb-6 relative">
              <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
                <Key className="w-5 h-5 text-purple-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Change Password</h2>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Current Password</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all"
                  placeholder="Minimum 8 characters"
                />
              </div>

              {passwordError && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2">
                  <p className="text-red-500 text-sm">{passwordError}</p>
                </div>
              )}

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={passwordLoading}
                  className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-5 py-2.5 shadow-md hover:shadow-lg transition-all disabled:opacity-50"
                >
                  {passwordLoading ? 'Updating…' : 'Update Password'}
                </button>
                {passwordSaved && (
                  <span className="flex items-center gap-1 text-green-500 text-sm">
                    <Check className="w-4 h-4" />Password updated.
                  </span>
                )}
              </div>
            </form>
          </div>
        </div>

        {/* Analysis History */}
        <div className="bg-white rounded-3xl border border-gray-100 shadow-lg overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-100 flex items-center gap-3 bg-gray-50/50">
            <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center shadow-md">
              <History className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Analysis History</h2>
          </div>

          {sessions.length === 0 ? (
            <div className="p-8 text-center text-muted">No analyses yet.</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {sessions.map((session) => (
                <div
                  key={session.session_id}
                  onClick={() => navigate(`/results?session=${session.session_id}`)}
                  className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-muted" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{session.label}</p>
                    <p className="text-sm text-muted">{formatDate(session.created_at)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-600">{session.total_reviews.toLocaleString()} reviews</p>
                    <p className={`text-sm font-semibold ${getScoreColor(session.overall_score)}`}>
                      {session.overall_score}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
