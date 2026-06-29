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
          Duplicates are removed, very short or nonsensical entries are filtered out, and the text is
          prepared for analysis. You see the count of reviews that made it through this stage.
        </Step>
        <Step number={2} title="Each review is classified across 7 dimensions">
          Overall feeling (positive, negative, or neutral) — which area of your business it is about
          (your custom categories) — how urgent the issue is — what emotion the customer is expressing
          — whether the review touches on multiple issues — a one-line summary of the core problem —
          and how confident the system is in the classification.
        </Step>
        <Step number={3} title="Everything is aggregated into your dashboard">
          Counts, percentages, and charts that surface patterns across all your reviews at once. Instead
          of reading 200 reviews yourself, you see the headline findings in seconds.
        </Step>
        <Step number={4} title="The AI Action Plan analyses the patterns">
          It reads the aggregated statistics and writes specific, ranked recommendations for your
          business — based on what your customers are actually saying, not generic advice.
        </Step>
      </div>
    </div>
  );
}

function DashboardTab() {
  return (
    <div>
      <P>Here is what each number and chart on your dashboard means.</P>

      <Heading>Overview Cards</Heading>
      <MetricRow label="Total Reviews">
        How many reviews were successfully analysed in this run. Reviews that were too short, duplicated,
        or unreadable are not counted.
      </MetricRow>
      <MetricRow label="Sentiment Score">
        A number from 0 to 100 representing your overall customer sentiment. Above 75 is strong.
        50 to 74 is mixed — room for improvement. Below 50 means more customers are unhappy than happy
        and needs immediate attention.
      </MetricRow>
      <MetricRow label="Positive Sentiment %">
        The percentage of reviews that expressed satisfaction. Higher is better. Compare this number
        across different analysis runs to see if you are improving.
      </MetricRow>
      <MetricRow label="Critical Issues">
        Reviews where customers expressed urgent, serious problems — things like receiving the wrong
        product, complete failure of service, or angry complaints. Even one critical issue deserves
        same-day attention.
      </MetricRow>

      <Heading>Charts</Heading>
      <MetricRow label="Feedback by Category">
        Shows which areas of your business customers mention most. A tall bar does not mean a problem
        — it means that area generates the most feedback, positive or negative. Look at the Urgency
        Heatmap to understand whether the volume is driven by complaints or compliments.
      </MetricRow>
      <MetricRow label="Urgency Heatmap">
        Cross-references your categories with urgency levels (Critical, Medium, Low). A dark red cell
        means multiple critical issues in that category — your highest priority area. Start with the
        darkest cell when deciding what to fix first.
      </MetricRow>
      <MetricRow label="Emotion Breakdown">
        Shows how customers feel. Happy and satisfied customers are likely to return and refer others.
        Angry and frustrated customers are likely to leave negative public reviews if not addressed
        quickly. The dominant emotion tells you the severity of the situation.
      </MetricRow>
      <MetricRow label="Top Negative Issues">
        The specific areas generating the most complaints, ranked by volume and urgency. Each row
        includes an example quote from a real review in your dataset. Start here when deciding what
        to fix first.
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
      <P>
        The AI Action Plan is generated from your actual feedback statistics — not generic advice.
        Every recommendation is tied to specific numbers from your data.
      </P>

      <Heading>Health Score</Heading>
      <P>
        A composite score combining your sentiment, urgency rate, and classification confidence.
        Think of it as your customer experience score for this batch of reviews.
      </P>
      <div style={{ background: '#F9FFFE', border: '1px solid #D1EDE6', borderRadius: '12px', padding: '16px', marginBottom: '20px' }}>
        <ScoreRow range="75 – 100" label="Strong">customers are largely satisfied</ScoreRow>
        <ScoreRow range="50 – 74" label="Mixed">clear areas for improvement</ScoreRow>
        <ScoreRow range="25 – 49" label="Needs Attention">significant customer experience problems</ScoreRow>
        <ScoreRow range="0 – 24" label="Critical">urgent action required</ScoreRow>
      </div>

      <Heading>Recommendations</Heading>
      <P>
        Ranked from highest to lowest impact. Each recommendation tells you what the data shows,
        what to do about it specifically, and how difficult it is to fix relative to the impact.
      </P>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
        {[
          { label: 'Impact', desc: 'How much fixing this will improve customer satisfaction. High impact issues are worth fixing even if they take effort.' },
          { label: 'Effort', desc: 'How much work is required. Low effort / high impact issues should always come first.' },
          { label: 'Timeframe', desc: 'When you should act. Immediate means this week. Short Term means this month. Long Term means this quarter.' },
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
      <P>
        The single easiest, fastest thing you can do right now to improve customer satisfaction
        based on your data. Always do this first — it is chosen because it has high impact and
        low effort, meaning you get a meaningful result quickly.
      </P>

      <Heading>Data Quality Note</Heading>
      <P>
        If this appears, it means some reviews were ambiguous and classified with lower confidence.
        This happens with very short reviews, reviews in multiple languages, or reviews that cover
        unusual topics. The overall patterns are still valid but treat individual category numbers
        with some caution.
      </P>
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
      a: 'CSV files (.csv) and Excel files (.xlsx or .xls). Make sure your file has a column containing the review text — FeedbackIQ will detect it automatically or let you choose it.',
    },
    {
      q: 'What are custom categories?',
      a: 'When you set up your company profile you define your own feedback categories — for example Delivery Speed, Product Quality, Customer Support. FeedbackIQ classifies every review into your categories, not generic ones. This makes the analysis specific to your business.',
    },
    {
      q: 'Why does a category show reviews even though I never mentioned that topic?',
      a: 'FeedbackIQ includes a General Experience category automatically as a catch-all for reviews that do not clearly fit any of your defined categories.',
    },
    {
      q: 'Can I run multiple analyses?',
      a: 'Yes. Every analysis is saved to your account history. After two or more analyses, FeedbackIQ will show you trend data — whether your sentiment is improving or declining over time.',
    },
    {
      q: 'Is my data secure?',
      a: 'Your password is encrypted using industry-standard hashing. Your review data is stored securely and never shared with other companies or used to train AI models.',
    },
    {
      q: 'Why did my action plan fail to generate?',
      a: 'The action plan occasionally hits usage limits. Wait 60 seconds and try again. If it continues to fail, try running the analysis again with your reviews.',
    },
    {
      q: 'What is the difference between Urgency and Sentiment?',
      a: 'Sentiment is about whether a review is positive or negative overall. Urgency is about how serious the problem is. A review can be negative but low urgency (mild dissatisfaction) or negative and critical urgency (angry, serious complaint requiring immediate action).',
    },
  ];

  return (
    <div>
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

        {/* Tabs — horizontal on md+, scrollable on mobile */}
        <div className="flex border-b border-gray-100 flex-shrink-0 overflow-x-auto"
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
