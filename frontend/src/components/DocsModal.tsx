import { useState, useEffect } from 'react';
import { X, BookOpen } from 'lucide-react';

interface DocsModalProps {
  onClose: () => void;
}

type TabId = 'how-it-works' | 'dashboard' | 'action-plan' | 'faq';

const TABS: { id: TabId; label: string }[] = [
  { id: 'how-it-works', label: 'How It Works' },
  { id: 'dashboard', label: 'Reading Your Dashboard' },
  { id: 'action-plan', label: 'Your AI Action Plan' },
  { id: 'faq', label: 'FAQ' },
];

const TEAL = '#0F6E56';
const BODY = '#4A4A4A';

function Heading({ children }: { children: React.ReactNode }) {
  return (
    <h3 style={{ color: TEAL, fontSize: '16px', fontWeight: 700, marginTop: '28px', marginBottom: '8px' }}>
      {children}
    </h3>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return <p style={{ margin: '0 0 14px 0' }}>{children}</p>;
}

function Step({ number, title, children }: { number: number; title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: '16px', marginBottom: '20px' }}>
      <div style={{
        flexShrink: 0, width: '32px', height: '32px', borderRadius: '50%',
        background: TEAL, color: 'white', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        fontWeight: 700, fontSize: '14px', marginTop: '2px',
      }}>
        {number}
      </div>
      <div>
        <p style={{ fontWeight: 600, color: '#1A1A1A', margin: '0 0 4px 0' }}>{title}</p>
        <p style={{ margin: 0, color: BODY }}>{children}</p>
      </div>
    </div>
  );
}

function MetricRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ borderLeft: `3px solid ${TEAL}`, paddingLeft: '14px', marginBottom: '20px' }}>
      <p style={{ fontWeight: 700, color: '#1A1A1A', margin: '0 0 4px 0', fontSize: '15px' }}>{label}</p>
      <p style={{ margin: 0, color: BODY }}>{children}</p>
    </div>
  );
}

function ScoreRow({ range, label, children }: { range: string; label: string; children?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: '12px', marginBottom: '10px', alignItems: 'flex-start' }}>
      <span style={{
        flexShrink: 0, background: '#E8F5F1', color: TEAL,
        fontWeight: 700, fontSize: '12px', padding: '2px 8px',
        borderRadius: '20px', whiteSpace: 'nowrap', marginTop: '2px',
      }}>
        {range}
      </span>
      <span style={{ color: BODY }}>
        <strong style={{ color: '#1A1A1A' }}>{label}</strong>
        {children && <> — {children}</>}
      </span>
    </div>
  );
}

function QA({ q, children }: { q: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: '24px' }}>
      <p style={{ fontWeight: 700, color: '#1A1A1A', margin: '0 0 6px 0' }}>{q}</p>
      <p style={{ margin: 0, color: BODY }}>{children}</p>
    </div>
  );
}

function HowItWorksTab() {
  return (
    <div>
      <P>
        FeedbackIQ reads your customer reviews and automatically identifies patterns you would otherwise
        spend hours finding manually.
      </P>
      <P>Here is what happens when you upload reviews:</P>
      <div style={{ marginTop: '24px' }}>
        <Step number={1} title="We read every review and clean it up">
          We read every review and remove duplicates and noise automatically.
        </Step>
        <Step number={2} title="Each review is classified across 7 dimensions">
          Each review is classified across 7 dimensions: overall sentiment (positive, negative, or neutral), which category of your business it relates to, urgency level, customer emotion, whether it covers multiple issues, a one-line core issue summary, and classification confidence.
        </Step>
        <Step number={3} title="Everything is aggregated into your dashboard">
          We aggregate everything into your dashboard — counts, percentages, and charts that surface patterns across all reviews instantly.
        </Step>
        <Step number={4} title="The AI Action Plan analyses the patterns">
          The AI Action Plan analyses these patterns and writes specific recommendations based on what your customers are actually saying.
        </Step>
      </div>
    </div>
  );
}

function DashboardTab() {
  return (
    <div>
      <P>Your dashboard turns raw review data into clear numbers and charts. Here is exactly what each element means and how to act on it.</P>

      <Heading>Overview Cards</Heading>
      <MetricRow label="Total Reviews">
        The number of reviews successfully analysed in this run. Duplicates and noise are removed automatically before counting.
      </MetricRow>
      <MetricRow label="Sentiment Score">
        A score from 0 to 100 representing overall customer sentiment. Above 75 is strong. 50 to 74 is mixed with room for improvement. Below 50 means more customers are unhappy than happy and needs immediate attention.
      </MetricRow>
      <MetricRow label="Positive Sentiment %">
        The percentage of reviews that expressed overall satisfaction. Track this across multiple analyses to see if your improvements are working.
      </MetricRow>
      <MetricRow label="Critical Issues">
        Reviews where customers expressed urgent, serious problems. Even one critical issue deserves same-day attention — these customers are most likely to leave public negative reviews.
      </MetricRow>

      <Heading>Charts</Heading>
      <MetricRow label="Feedback by Category">
        Shows which areas of your business customers mention most. A tall bar does not automatically mean a problem — it means that area generates the most feedback, positive or negative. Check the urgency heatmap to understand if it is good or bad attention.
      </MetricRow>
      <MetricRow label="Urgency Heatmap">
        Cross-references your categories with urgency levels. A red cell means multiple critical issues in that category — your highest priority area to fix.
      </MetricRow>
      <MetricRow label="Emotion Breakdown">
        Shows how customers feel emotionally. Happy and satisfied customers are likely to return and refer others. Angry and frustrated customers are likely to leave negative public reviews if not addressed quickly.
      </MetricRow>
      <MetricRow label="Top Negative Issues">
        The specific areas generating the most complaints, ranked by volume and then by critical count. Always start here when deciding what to fix first.
      </MetricRow>
      <MetricRow label="Multi-Aspect Coverage">
        Shows how many reviews mention more than one topic. A high proportion of multi-aspect reviews
        often indicates systemic issues — customers who complain about both delivery and customer
        service at the same time are usually having a bad overall experience, not isolated incidents.
      </MetricRow>
    </div>
  );
}

function ActionPlanTab() {
  return (
    <div>
      <P>The AI Action Plan is generated from your actual feedback statistics — not generic advice. Every recommendation is tied to specific numbers from your data.</P>

      <Heading>Health Score</Heading>
      <P>A composite score combining your sentiment rate, urgency rate, and classification confidence. Think of it as your overall customer experience score for this batch of reviews.</P>
      <div style={{ background: '#F9FFFE', border: '1px solid #D1EDE6', borderRadius: '12px', padding: '16px', marginBottom: '20px' }}>
        <ScoreRow range="75 – 100" label="Strong">customers are largely satisfied</ScoreRow>
        <ScoreRow range="50 – 74" label="Mixed">clear areas needing improvement</ScoreRow>
        <ScoreRow range="25 – 49" label="Needs Attention">significant customer experience problems</ScoreRow>
        <ScoreRow range="0 – 24" label="Critical">urgent action required immediately</ScoreRow>
      </div>

      <Heading>Recommendations</Heading>
      <P>Ranked from highest to lowest impact. Each recommendation tells you what the data shows, exactly what to do about it, and how hard it is to fix relative to the impact it will have.</P>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
        {[
          { label: 'Impact', desc: 'How much fixing this issue will improve overall customer satisfaction based on the volume and urgency of complaints.' },
          { label: 'Effort', desc: 'How much work is required from your team. Low effort means you can act this week. High effort means it needs planning and resources.' },
          { label: 'Timeframe', desc: 'Immediate means act this week. Short Term means act this month. Long Term means plan for this quarter.' },
        ].map(({ label, desc }) => (
          <div key={label} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <span style={{ flexShrink: 0, background: TEAL, color: 'white', fontWeight: 700, fontSize: '11px', padding: '3px 10px', borderRadius: '20px', marginTop: '2px' }}>
              {label}
            </span>
            <span style={{ color: BODY }}>{desc}</span>
          </div>
        ))}
      </div>

      <Heading>Quick Win</Heading>
      <P>The single easiest, fastest thing you can do right now to improve customer satisfaction. Always do this first — it builds momentum and shows customers you are listening.</P>

      <Heading>Data Quality Note</Heading>
      <P>Appears when some reviews were ambiguous and classified with lower confidence. The overall patterns are still valid but treat individual category numbers with some caution.</P>
    </div>
  );
}

function FaqTab() {
  const items: { q: string; a: React.ReactNode }[] = [
    {
      q: 'How many reviews can I analyse at once?',
      a: 'Up to 2,000 reviews per analysis when uploading a file, or up to 100 reviews when pasting text directly.',
    },
    {
      q: 'What file formats can I upload?',
      a: 'CSV files (.csv) and Excel files (.xlsx or .xls). Make sure your file has a column containing the review text — FeedbackIQ detects it automatically or lets you choose it manually.',
    },
    {
      q: 'What are custom categories?',
      a: 'When you set up your company profile you define your own feedback categories — for example Delivery Speed, Product Quality, or Customer Support. FeedbackIQ classifies every review into your categories specifically, not generic ones. This makes the analysis relevant to your exact business.',
    },
    {
      q: 'Why do some reviews appear under General Experience?',
      a: 'FeedbackIQ adds a General Experience category automatically as a catch-all for reviews that do not clearly fit any of your defined categories.',
    },
    {
      q: 'Can I run multiple analyses?',
      a: 'Yes. Every analysis is saved to your account history. After two or more analyses FeedbackIQ shows you trend data — whether your sentiment score is improving or declining over time.',
    },
    {
      q: 'Is my data secure?',
      a: 'Your password is encrypted using Argon2 — the same industry-standard algorithm used by major password managers. Your review data is stored securely and never shared with other companies.',
    },
    {
      q: 'Why did my action plan fail to generate?',
      a: 'The AI model occasionally hits usage limits. Wait 60 seconds and click Generate Action Plan again. If it keeps failing, try re-running the analysis.',
    },
    {
      q: 'What is the difference between Urgency and Sentiment?',
      a: 'Sentiment is whether a review is positive or negative overall. Urgency is how serious the problem is. A review can be negative but low urgency — mild dissatisfaction — or negative and critical urgency — an angry complaint needing immediate action.',
    },
  ];

  return (
    <div>
      <P>Answers to the most common questions about how FeedbackIQ works.</P>
      {items.map(({ q, a }) => (
        <QA key={q} q={q}>{a}</QA>
      ))}
    </div>
  );
}

export default function DocsModal({ onClose }: DocsModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>('how-it-works');

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  // Prevent body scroll while modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4 sm:p-6"
      style={{ backdropFilter: 'blur(6px)', backgroundColor: 'rgba(0,0,0,0.45)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full flex flex-col"
        style={{ maxWidth: '720px', maxHeight: '90vh' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 flex-shrink-0"
             style={{ padding: '20px 32px' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl gradient-bg flex items-center justify-center flex-shrink-0">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-xs font-bold tracking-wide" style={{ color: TEAL, marginBottom: '1px' }}>
                FeedbackIQ
              </p>
              <h2 className="font-bold text-gray-900 leading-tight" style={{ fontSize: '17px' }}>
                Understanding Your FeedbackIQ Report
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-xl hover:bg-gray-100 flex items-center justify-center text-gray-400 hover:text-gray-700 transition-colors flex-shrink-0"
            style={{ width: '36px', height: '36px' }}
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs — horizontal on sm+, stacked on mobile */}
        <style>{`
          @media (min-width: 640px) {
            .docs-tab-list { flex-direction: row; }
          }
        `}</style>
        <div className="docs-tab-list flex flex-col border-b border-gray-100 flex-shrink-0"
             style={{ padding: '0 32px' }}>
          {TABS.map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="transition-all whitespace-nowrap"
                style={{
                  padding: '14px 16px',
                  fontSize: '14px',
                  fontWeight: active ? 600 : 500,
                  color: active ? TEAL : '#6B7280',
                  background: 'none',
                  border: 'none',
                  borderBottom: active ? `2px solid ${TEAL}` : '2px solid transparent',
                  cursor: 'pointer',
                  marginBottom: '-1px',
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Scrollable body */}
        <div
          className="overflow-y-auto flex-1"
          style={{ padding: '32px', color: BODY, fontSize: '15px', lineHeight: '1.7' }}
        >
          {activeTab === 'how-it-works' && <HowItWorksTab />}
          {activeTab === 'dashboard' && <DashboardTab />}
          {activeTab === 'action-plan' && <ActionPlanTab />}
          {activeTab === 'faq' && <FaqTab />}
        </div>
      </div>
    </div>
  );
}
