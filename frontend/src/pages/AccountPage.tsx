import { useState, useEffect, FormEvent, KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, Briefcase, Key, History, Save, Check, X, Mail, Calendar,
  BarChart3, Link, Bell, AlertTriangle, Trash2, Send, Copy,
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import { getMe, updateProfile, changePassword } from '../api/auth';
import { listSessions } from '../api/sessions';
import { getWebhook, registerWebhook, deleteWebhook, testWebhook } from '../api/webhooks';
import type { UserMeResponse, SessionSummary } from '../types/api';
import type { WebhookConfig, TestWebhookResult } from '../api/webhooks';

const INDUSTRIES = [
  { value: 'E-commerce',  label: 'E-commerce' },
  { value: 'SaaS',        label: 'SaaS / Software' },
  { value: 'Retail',      label: 'Retail' },
  { value: 'Hospitality', label: 'Hospitality & Restaurants' },
  { value: 'Healthcare',  label: 'Healthcare' },
  { value: 'Logistics',   label: 'Logistics & Delivery' },
  { value: 'Finance',     label: 'Finance & Banking' },
  { value: 'Education',   label: 'Education' },
  { value: 'Other',       label: 'Other' },
];

const EVENT_OPTIONS = [
  {
    id: 'critical_spike',
    label: 'Critical Spike',
    description: 'Critical issues exceed 20% of reviews',
  },
  {
    id: 'sentiment_drop',
    label: 'Sentiment Drop',
    description: 'Overall score drops 10+ points',
  },
  {
    id: 'new_top_issue',
    label: 'New Top Issue',
    description: 'A new category becomes your #1 problem',
  },
];

type Tab = 'profile' | 'security' | 'webhooks';

export default function AccountPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [meData, setMeData] = useState<UserMeResponse | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);

  // ── Profile form ───────────────────────────────────────────────────────────
  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('E-commerce');
  const [categories, setCategories] = useState<string[]>([]);
  const [categoryInput, setCategoryInput] = useState('');
  const [description, setDescription] = useState('');
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  // ── Password form ──────────────────────────────────────────────────────────
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // ── Webhook tab ────────────────────────────────────────────────────────────
  const [webhookConfig, setWebhookConfig] = useState<WebhookConfig | null>(null);
  const [webhookLoading, setWebhookLoading] = useState(true);
  const [webhookUrl, setWebhookUrl] = useState('https://');
  const [webhookEvents, setWebhookEvents] = useState<string[]>([]);
  const [webhookSaving, setWebhookSaving] = useState(false);
  const [webhookError, setWebhookError] = useState<string | null>(null);
  const [registrationSecret, setRegistrationSecret] = useState<string | null>(null);
  const [secretCopied, setSecretCopied] = useState(false);
  const [testResult, setTestResult] = useState<TestWebhookResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    getMe()
      .then((data) => {
        setMeData(data);
        if (data.profile) {
          setCompanyName(data.profile.company_name || '');
          setIndustry(data.profile.industry || 'E-commerce');
          setCategories(data.profile.categories || []);
          setDescription(data.profile.description || '');
        }
        const stored = localStorage.getItem('user_data');
        const existing = stored ? JSON.parse(stored) : {};
        localStorage.setItem('user_data', JSON.stringify({ ...existing, full_name: data.full_name, email: data.email }));
      })
      .catch(() => {});

    listSessions()
      .then((r) => setSessions(r.sessions))
      .catch(() => setSessions([]));

    getWebhook()
      .then((r) => {
        if (r.registered) setWebhookConfig(r);
        else setWebhookConfig(null);
      })
      .catch(() => setWebhookConfig(null))
      .finally(() => setWebhookLoading(false));
  }, []);

  // ── Profile handlers ───────────────────────────────────────────────────────
  const handleAddCategory = () => {
    const trimmed = categoryInput.trim();
    if (trimmed && !categories.includes(trimmed) && categories.length < 8) {
      setCategories([...categories, trimmed]);
      setCategoryInput('');
    }
  };

  const handleCategoryKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') { e.preventDefault(); handleAddCategory(); }
  };

  const handleSaveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setProfileLoading(true);
    setProfileSaved(false);
    setProfileError(null);
    try {
      await updateProfile({ company_name: companyName, industry, categories, description: description || null, urgency_definition: null });
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: unknown } } };
      const d = ax?.response?.data?.detail;
      setProfileError(typeof d === 'string' ? d : 'Failed to save profile.');
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
      const ax = err as { response?: { data?: { detail?: unknown } } };
      const d = ax?.response?.data?.detail;
      setPasswordError(typeof d === 'string' ? d : 'Failed to update password.');
    } finally {
      setPasswordLoading(false);
    }
  };

  // ── Webhook handlers ───────────────────────────────────────────────────────
  const handleRegisterWebhook = async (e: FormEvent) => {
    e.preventDefault();
    if (!webhookUrl.startsWith('https://')) {
      setWebhookError('Webhook URL must start with https://');
      return;
    }
    if (webhookEvents.length === 0) {
      setWebhookError('Select at least one event to subscribe to.');
      return;
    }
    setWebhookSaving(true);
    setWebhookError(null);
    try {
      const reg = await registerWebhook(webhookUrl, webhookEvents);
      setRegistrationSecret(reg.webhook_secret);
      setWebhookConfig({
        registered: true,
        url: reg.url,
        events: reg.events,
        active: reg.active,
        created_at: reg.created_at,
        last_triggered: null,
      });
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: unknown } } };
      const d = ax?.response?.data?.detail;
      setWebhookError(typeof d === 'string' ? d : 'Failed to register webhook.');
    } finally {
      setWebhookSaving(false);
    }
  };

  const handleTestWebhook = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testWebhook();
      setTestResult(result);
    } catch {
      setTestResult({ delivered: false, status_code: null, error: 'Request failed' });
    } finally {
      setTesting(false);
    }
  };

  const handleDeleteWebhook = async () => {
    setDeleting(true);
    try {
      await deleteWebhook();
      setWebhookConfig(null);
      setRegistrationSecret(null);
      setWebhookUrl('https://');
      setWebhookEvents([]);
      setDeleteConfirm(false);
    } catch {
      // silently ignore
    } finally {
      setDeleting(false);
    }
  };

  const handleCopySecret = () => {
    if (registrationSecret) {
      navigator.clipboard.writeText(registrationSecret).then(() => {
        setSecretCopied(true);
        setTimeout(() => setSecretCopied(false), 2000);
      });
    }
  };

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });

  const getScoreColor = (score: number) =>
    score >= 75 ? 'text-green-500' : score >= 50 ? 'text-amber-500' : 'text-red-500';

  const displayName = meData?.full_name || 'User';
  const initials = displayName.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2);

  const examplePayload = JSON.stringify({
    version: '1.0',
    event: 'critical_spike',
    triggered_at: new Date().toISOString(),
    session_id: 'uuid-...',
    company_name: meData?.profile?.company_name || 'Your Company',
    industry: meData?.profile?.industry || 'Your Industry',
    data: { critical_count: 12, critical_pct: 24.0, threshold: 20.0 },
  }, null, 2);

  const tabs: { id: Tab; label: string; icon: typeof Building2 }[] = [
    { id: 'profile', label: 'Profile', icon: Building2 },
    { id: 'security', label: 'Security', icon: Key },
    { id: 'webhooks', label: 'Webhooks', icon: Link },
  ];

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

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-2xl w-fit">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                activeTab === id
                  ? 'bg-white text-primary shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="bg-white rounded-3xl border border-gray-100 shadow-lg p-6 overflow-hidden relative mb-8">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-blue-500 to-cyan-400" />
            <div className="flex items-center gap-3 mb-6 relative">
              <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-blue-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Company Profile</h2>
            </div>
            <form onSubmit={handleSaveProfile} className="space-y-4 max-w-lg">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Company Name</label>
                <input type="text" value={companyName} onChange={(e) => setCompanyName(e.target.value)} required
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all"
                  placeholder="Acme Corp" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Briefcase className="w-4 h-4 inline mr-1" />Industry
                </label>
                <select value={industry} onChange={(e) => setIndustry(e.target.value)}
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 bg-white transition-all">
                  {INDUSTRIES.map((ind) => <option key={ind.value} value={ind.value}>{ind.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Categories</label>
                <div className="flex gap-2 mb-2">
                  <input type="text" value={categoryInput} onChange={(e) => setCategoryInput(e.target.value)}
                    onKeyDown={handleCategoryKeyDown} disabled={categories.length >= 8}
                    className="flex-1 border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 disabled:bg-gray-50 transition-all"
                    placeholder="Add category…" />
                  <button type="button" onClick={handleAddCategory} disabled={!categoryInput.trim() || categories.length >= 8}
                    className="px-4 rounded-xl bg-primary/10 text-primary hover:bg-primary hover:text-white transition-all disabled:opacity-50">
                    Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {categories.map((cat) => (
                    <span key={cat} className="inline-flex items-center gap-1.5 px-3 py-1.5 gradient-bg-light text-primary rounded-xl text-sm font-medium border border-primary/20">
                      {cat}
                      <button type="button" onClick={() => setCategories(categories.filter((c) => c !== cat))} className="hover:text-red-500">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2}
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 resize-none transition-all"
                  placeholder="Brief description of your company…" />
              </div>
              {profileError && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2">
                  <p className="text-red-500 text-sm">{profileError}</p>
                </div>
              )}
              <div className="flex items-center gap-3 pt-2">
                <button type="submit" disabled={profileLoading || categories.length < 1}
                  className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-5 py-2.5 shadow-md hover:shadow-lg transition-all disabled:opacity-50">
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
        )}

        {/* Security Tab */}
        {activeTab === 'security' && (
          <div className="bg-white rounded-3xl border border-gray-100 shadow-lg p-6 overflow-hidden relative mb-8">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-purple-500 to-pink-400" />
            <div className="flex items-center gap-3 mb-6 relative">
              <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
                <Key className="w-5 h-5 text-purple-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Change Password</h2>
            </div>
            <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Current Password</label>
                <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">New Password</label>
                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8}
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all"
                  placeholder="Minimum 8 characters" />
              </div>
              {passwordError && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2">
                  <p className="text-red-500 text-sm">{passwordError}</p>
                </div>
              )}
              <div className="flex items-center gap-3 pt-2">
                <button type="submit" disabled={passwordLoading}
                  className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-5 py-2.5 shadow-md hover:shadow-lg transition-all disabled:opacity-50">
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
        )}

        {/* Webhooks Tab */}
        {activeTab === 'webhooks' && (
          <div className="bg-white rounded-3xl border border-gray-100 shadow-lg p-6 overflow-hidden relative mb-8">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-teal-500 to-cyan-400" />
            <div className="flex items-center gap-3 mb-6 relative">
              <div className="w-10 h-10 rounded-xl bg-teal-100 flex items-center justify-center">
                <Bell className="w-5 h-5 text-teal-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Webhooks</h2>
                <p className="text-muted text-sm">Get instant notifications when critical issues are detected</p>
              </div>
            </div>

            {webhookLoading ? (
              <div className="animate-pulse h-24 bg-gray-100 rounded-xl" />
            ) : !webhookConfig ? (
              <>
                {/* Secret shown once after registration */}
                {registrationSecret && (
                  <div className="mb-6 bg-green-50 border border-green-200 rounded-xl p-4">
                    <p className="text-green-800 font-semibold text-sm mb-2 flex items-center gap-2">
                      <Check className="w-4 h-4" />Webhook registered! Save your secret now — it will not be shown again.
                    </p>
                    <div className="flex items-center gap-2 bg-white border border-green-200 rounded-lg px-3 py-2 font-mono text-xs text-gray-800 break-all">
                      <span className="flex-1">{registrationSecret}</span>
                      <button onClick={handleCopySecret} className="text-green-600 hover:text-green-800 flex-shrink-0">
                        {secretCopied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                )}

                {/* Info card */}
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
                  <p className="text-blue-800 text-sm">
                    Get instant notifications when FeedbackIQ detects critical issues in your feedback.
                    Connect your Slack, PagerDuty, or any service that accepts webhooks.
                  </p>
                </div>

                {/* Registration form */}
                <form onSubmit={handleRegisterWebhook} className="space-y-4 max-w-lg">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Webhook URL</label>
                    <input type="url" value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} required
                      className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 font-mono text-sm transition-all"
                      placeholder="https://example.com/webhook" />
                    <p className="text-xs text-muted mt-1">Must use HTTPS</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">Events to Subscribe</label>
                    <div className="space-y-3">
                      {EVENT_OPTIONS.map(({ id, label, description }) => (
                        <label key={id} className="flex items-start gap-3 cursor-pointer group">
                          <input
                            type="checkbox"
                            checked={webhookEvents.includes(id)}
                            onChange={(e) => {
                              if (e.target.checked) setWebhookEvents([...webhookEvents, id]);
                              else setWebhookEvents(webhookEvents.filter((ev) => ev !== id));
                            }}
                            className="mt-0.5 w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                          />
                          <div>
                            <p className="text-sm font-medium text-gray-800 group-hover:text-primary transition-colors">{label}</p>
                            <p className="text-xs text-muted">{description}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {webhookError && (
                    <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2">
                      <p className="text-red-500 text-sm">{webhookError}</p>
                    </div>
                  )}

                  <button type="submit" disabled={webhookSaving}
                    className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-5 py-2.5 shadow-md hover:shadow-lg transition-all disabled:opacity-50">
                    <Link className="w-4 h-4" />
                    {webhookSaving ? 'Registering…' : 'Register Webhook'}
                  </button>
                </form>
              </>
            ) : (
              <>
                {/* Registered webhook details */}
                <div className="space-y-4 max-w-lg">
                  <div className="border border-gray-100 rounded-xl p-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">URL</p>
                    <p className="font-mono text-sm text-gray-800 truncate">
                      {webhookConfig.url.slice(0, 40)}{webhookConfig.url.length > 40 ? '…' : ''}
                    </p>
                  </div>

                  <div className="border border-gray-100 rounded-xl p-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Subscribed Events</p>
                    <div className="flex flex-wrap gap-2">
                      {webhookConfig.events.map((ev) => (
                        <span key={ev} className="px-3 py-1 bg-teal-100 text-teal-700 rounded-full text-xs font-semibold">{ev}</span>
                      ))}
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-3">
                    <button onClick={handleTestWebhook} disabled={testing}
                      className="flex items-center gap-2 border-2 border-primary text-primary rounded-xl px-4 py-2 hover:bg-primary/5 transition-all text-sm font-semibold disabled:opacity-50">
                      <Send className="w-4 h-4" />
                      {testing ? 'Sending…' : 'Send Test'}
                    </button>
                    {!deleteConfirm ? (
                      <button onClick={() => setDeleteConfirm(true)}
                        className="flex items-center gap-2 border-2 border-red-200 text-red-500 rounded-xl px-4 py-2 hover:bg-red-50 transition-all text-sm font-semibold">
                        <Trash2 className="w-4 h-4" />
                        Delete Webhook
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-red-600 font-medium">Are you sure?</span>
                        <button onClick={handleDeleteWebhook} disabled={deleting}
                          className="bg-red-500 text-white rounded-xl px-3 py-2 text-sm font-semibold hover:bg-red-600 transition-all disabled:opacity-50">
                          {deleting ? 'Deleting…' : 'Yes, delete'}
                        </button>
                        <button onClick={() => setDeleteConfirm(false)} className="text-sm text-muted hover:text-gray-600">Cancel</button>
                      </div>
                    )}
                  </div>

                  {/* Test result */}
                  {testResult && (
                    <div className={`rounded-xl px-4 py-3 border text-sm ${
                      testResult.delivered ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'
                    }`}>
                      {testResult.delivered
                        ? `Test delivered successfully (HTTP ${testResult.status_code})`
                        : `Test failed: ${testResult.error || 'Unknown error'}`
                      }
                    </div>
                  )}

                  {/* Example payload */}
                  <div>
                    <p className="text-sm font-semibold text-gray-700 mb-2">Example Payload</p>
                    <pre className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs font-mono text-gray-700 overflow-x-auto whitespace-pre-wrap">
                      {examplePayload}
                    </pre>
                  </div>

                  {/* Secret note */}
                  <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <p className="text-amber-800 text-xs">
                      Your webhook secret was shown once at registration. Store it securely to verify incoming requests using HMAC-SHA256 on the <code className="font-mono">X-FeedbackIQ-Signature</code> header.
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

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
                <div key={session.session_id}
                  onClick={() => navigate(`/results?session=${session.session_id}`)}
                  className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors">
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
