# FeedbackIQ — Frontend Handoff Document

**Generated from live API on 2026-06-26. Frozen spec: `api/openapi.json` (15 paths).**

---

## Section 1 — Stack and base URL

**Frontend stack:** React 18 + TypeScript + Tailwind CSS + React Router v6.

**API base URL:**
- Development: `http://localhost:8000`
- All relative paths below are appended to this base.

**Default request header** (all JSON endpoints):
```
Content-Type: application/json
```
Exception: `POST /analyse/text` uses `application/x-www-form-urlencoded`. `POST /analyse/file` uses `multipart/form-data`. Both still include the `Authorization` header.

**Auth header** (all protected endpoints):
```
Authorization: Bearer {access_token}
```
Where `access_token` is read from `localStorage.getItem('access_token')`.

---

## Section 2 — Auth flow

### Signup
`POST /auth/signup` — JSON body: `{ email, password, full_name }`
- On 201: store `access_token` and `refresh_token` in `localStorage`. Redirect to `/dashboard`.

### Login
`POST /auth/login` — **form-data** body: `username={email}&password={password}` (Content-Type: `application/x-www-form-urlencoded`).
- On 200: store `access_token` and `refresh_token` in `localStorage`. Redirect to `/dashboard`.

### Token attachment
On every API call, read `localStorage.getItem('access_token')` and attach as `Authorization: Bearer {token}`. Use an axios interceptor on the request to do this automatically.

### Token refresh
On any **401 response**, attempt one automatic refresh:
1. Call `POST /auth/refresh` with JSON body `{ refresh_token: localStorage.getItem('refresh_token') }`.
2. On 200: store new `access_token` in `localStorage`. Retry the original failed request exactly once.
3. On any failure (non-200, or network error): clear `localStorage` (`removeItem('access_token')`, `removeItem('refresh_token')`), redirect to `/login`.

### Logout
Clear `localStorage` (both tokens). Redirect to `/login`.

### Guard rule
On any screen that calls `GET /auth/me` and receives 401: clear storage immediately and redirect to `/login` without showing any error UI.

---

## Section 3 — Screens and their API calls

### Screen 1: Landing / Login
**Route:** `/login`
**Purpose:** Unauthenticated entry point.
**API calls:**
- `POST /auth/login` (form-data: `username`, `password`) → stores tokens, redirects to `/dashboard`

**Layout:** Centered card with FeedbackIQ logo, email and password fields, "Log In" button, link to `/signup`.

---

### Screen 2: Signup
**Route:** `/signup`
**Purpose:** New account creation.
**API calls:**
- `POST /auth/signup` (JSON: `email`, `password`, `full_name`) → stores tokens, redirects to `/dashboard`

**Layout:** Centered card with full name, email, and password fields, "Create Account" button, link to `/login`.

---

### Screen 3: Home Dashboard
**Route:** `/dashboard`
**Purpose:** Authenticated home — shows session history and a "New Analysis" CTA.
**API calls:**
- `GET /auth/me` → display user's `full_name` in top-right nav chip
- `GET /sessions` → populate the history table (columns: Company, Date, Reviews, Score, Actions)

**Layout:** Top navbar with logo + user chip + logout. Page body: "New Analysis" button (primary, links to `/analyse/profile`). Below: session history table. Clicking a row navigates to `/results?session={session_id}`.

---

### Screen 4: New Analysis — Step 1: Profile
**Route:** `/analyse/profile`
**Purpose:** Collect company profile before creating a session.
**API calls:**
- `GET /auth/profile` → pre-fills form fields if a saved profile exists; on 404, show empty form (no error)
- `POST /sessions` (JSON: `company_name`, `industry`, `categories`, `description?`, `urgency_definition?`) → creates session, stores `session_id`, navigates to `/analyse/upload?session={session_id}`
- `PUT /auth/profile` (JSON: same fields) → called only if "Save profile for next time" checkbox is ticked, called before `POST /sessions` so the user's profile is persisted

**Layout:** Two-column form. Left: Company Name, Industry, Description (textarea). Right: Categories (multi-tag input, 2–8 items), Urgency Definition (textarea). Bottom: "Save profile" checkbox, "Next →" button.

---

### Screen 5: New Analysis — Step 2: Upload
**Route:** `/analyse/upload?session={id}`
**Purpose:** Submit review data for classification.
**API calls:**
- `POST /analyse/text` (form-data: `session_id`, `raw_text`) → on 200, navigate to `/analyse/processing?session={id}`
- `POST /analyse/file` (multipart: `session_id`, `file`, `column?`) → on 200, navigate to `/analyse/processing?session={id}`

**Layout:** Two tabs — "Paste Text" and "Upload File". Paste tab: large textarea. File tab: drag-and-drop zone (accepts `.csv`, `.xlsx`, `.xls`); after file selection show detected column name with an override dropdown. Both tabs show a "Run Analysis" button.

---

### Screen 6: Processing
**Route:** `/analyse/processing?session={id}`
**Purpose:** Show progress while classification runs in the background.
**API calls:**
- `GET /dashboard/{session_id}` — poll every 3 seconds
  - While `classification_done === false`: update progress bar (fake animation 0→90% over 30 s)
  - When `classification_done === true`: set progress to 100%, wait 1 s, redirect to `/results?session={id}`

**Layout:** Centered card with animated progress bar, status message ("Classifying your reviews…"), and `total_classified` counter that updates on each poll response.

---

### Screen 7: Results
**Route:** `/results?session={id}`
**Purpose:** Full analysis results — dashboard, action plan, downloads.
**API calls:**
- `GET /dashboard/{session_id}` → populate all metric cards, charts placeholders, and issues table
- `POST /action-plan/{session_id}` → triggered on "Generate Action Plan" button click; show spinner while loading; on 200, display health score and recommendations panel
- `GET /report/{session_id}` → on "Download PDF" button click; open URL in new tab: `window.open(API_BASE + '/report/' + sessionId + '?token=' + accessToken, '_blank')` — Note: append the token as a query param because new tabs cannot set headers. Alternatively, trigger a fetch with the token and use a Blob URL.
- `GET /export/{session_id}` → on "Export CSV" button click; fetch with auth header, create a `Blob` from the response, trigger a download via `<a href={blobUrl} download="feedbackiq_results.csv">`

**Layout:** Back arrow to `/dashboard`. Metric cards row (Total Reviews, Positive %, Critical Issues, Overall Score). Charts section (sentiment donut, emotion bar, category bar — use placeholder divs or recharts). Issues table. "Generate Action Plan" button (disabled and shows spinner while in-flight; on success, shows health score banner + recommendations cards). "Download PDF" and "Export CSV" buttons.

---

### Screen 8: Account
**Route:** `/account`
**Purpose:** User profile management and session history.
**API calls:**
- `GET /auth/me` → display email, full name, join date, session count
- `PUT /auth/profile` (JSON: `company_name`, `industry`, `categories`, `description?`, `urgency_definition?`) → update saved profile
- `POST /auth/change-password` (JSON: `current_password`, `new_password`) → on 200, show success toast
- `GET /auth/history` → list past sessions in a compact table

**Layout:** Two panels side by side. Left: Profile form (company name, industry, categories, description, urgency definition) + save button. Right: Change Password form (current password, new password) + submit button. Below: Session history table.

---

## Section 4 — Request and response shapes

All TypeScript interfaces are derived directly from `api/openapi.json` schemas, with `dashboard_data` and `action_plan.result` expanded from implementation knowledge.

```typescript
// ── Auth ──────────────────────────────────────────────────────────────

interface SignupRequest {
  email: string;          // validated: must be valid email format
  password: string;       // minLength: 8, maxLength: 128
  full_name: string;      // minLength: 1, maxLength: 100
}

// POST /auth/login — send as application/x-www-form-urlencoded
interface LoginFormData {
  username: string;       // the user's email address
  password: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;     // always "bearer"
  user_id: string;
  email: string;
  full_name: string;
  has_profile: boolean;
}

interface RefreshRequest {
  refresh_token: string;
}

interface UserMeResponse {
  user_id: string;
  email: string;
  full_name: string;
  created_at: string;     // ISO 8601 datetime
  last_login: string | null;
  profile: ProfileData | null;
  session_count: number;
  has_profile: boolean;
}

interface ProfileData {
  company_name: string;
  industry: string;
  categories: string[];
  description?: string | null;
  urgency_definition?: string | null;
}

// GET /auth/profile → 200: ProfileData (same shape) | 404 (no profile saved)
// PUT /auth/profile → 200: { message: string }
interface ProfileUpdateRequest {
  company_name: string;   // minLength: 1, maxLength: 100
  industry: string;       // minLength: 1
  categories: string[];   // minItems: 2, maxItems: 8
  description?: string | null;
  urgency_definition?: string | null;
}

interface ChangePasswordRequest {
  current_password: string;
  new_password: string;   // minLength: 8, maxLength: 128
}

// POST /auth/change-password → 200: { message: string }

// GET /auth/history → 200: SessionsListResponse (same shape as GET /sessions)

// ── Sessions ──────────────────────────────────────────────────────────

interface CreateSessionRequest {
  company_name: string;   // minLength: 1, maxLength: 100
  industry: string;       // minLength: 1
  categories: string[];   // minItems: 2, maxItems: 8
  description?: string | null;
  urgency_definition?: string | null;
}

interface CreateSessionResponse {
  session_id: string;
  profile: ProfileData;
  created_at: string;     // ISO 8601 datetime
  user_id?: string | null;
}

interface SessionSummary {
  session_id: string;
  label: string;          // human-readable label, e.g. "Acme Corp — 2026-06-26"
  created_at: string;
  total_reviews: number;
  overall_score: number;
}

interface SessionsListResponse {
  sessions: SessionSummary[];
  total: number;
}

// ── Analysis ──────────────────────────────────────────────────────────

// POST /analyse/text — send as application/x-www-form-urlencoded
interface AnalyseTextFormData {
  session_id: string;
  raw_text: string;
}

// POST /analyse/file — send as multipart/form-data
interface AnalyseFileFormData {
  session_id: string;
  file: File;             // .csv, .xlsx, or .xls
  column?: string;        // override auto-detected review column name
}

interface PreprocessingSummary {
  input_count: number;
  final_count: number;
  noise_removed: number;
  exact_duplicates_removed: number;
  near_duplicates_removed: number;
  short_removed: number;
}

interface AnalyseResponse {
  session_id: string;
  total_classified: number;
  total_failed: number;
  gemini_fallback_count: number;
  failed_batches: unknown[];
  preprocessing: PreprocessingSummary;
}

// ── Dashboard ─────────────────────────────────────────────────────────

interface SentimentData {
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  positive_pct: number;
  negative_pct: number;
  neutral_pct: number;
  overall_score: number;
}

interface CategoryItem {
  category: string;
  count: number;
  pct: number;
}

interface UrgencyData {
  critical_count: number;
  medium_count: number;
  low_count: number;
  critical_pct: number;
}

interface EmotionItem {
  emotion: string;
  count: number;
  pct: number;
}

interface MultiAspectData {
  multi_aspect_count: number;
  multi_aspect_pct: number;
  single_aspect_count: number;
}

interface TopIssue {
  category: string;
  count: number;
  critical_count: number;
  example: string;
}

interface ConfidenceData {
  high_count: number;
  medium_count: number;
  low_count: number;
  low_pct: number;
}

interface HealthScoreInputs {
  positive_pct: number;
  critical_pct: number;
  low_confidence_pct: number;
}

// urgency_matrix is a serialised DataFrame returned as:
// { data: number[][], index: string[], columns: string[] }
interface UrgencyMatrixSplit {
  data: number[][];
  index: string[];         // category names
  columns: string[];       // ["critical", "medium", "low"]
}

interface DashboardData {
  total_reviews: number;
  sentiment: SentimentData;
  categories: CategoryItem[];
  urgency: UrgencyData;
  urgency_matrix: UrgencyMatrixSplit;
  emotions: EmotionItem[];
  multi_aspect: MultiAspectData;
  top_issues: TopIssue[];
  confidence: ConfidenceData;
  top_category: string;
  health_score_inputs: HealthScoreInputs;
}

interface DashboardResponse {
  session_id: string;
  profile: ProfileData;
  dashboard_data: DashboardData;
  classification_done: boolean;
  total_classified: number;
}

// ── Action Plan ───────────────────────────────────────────────────────

interface Recommendation {
  rank: number;
  title: string;
  rationale: string;
  action: string;
  impact: 'high' | 'medium' | 'low';
  effort: 'high' | 'medium' | 'low';
  timeframe: 'immediate' | 'short_term' | 'long_term';
}

interface QuickWin {
  title: string;
  description: string;
  expected_outcome: string;
}

interface ActionPlanResult {
  health_score: number;
  health_label: string;
  executive_summary: string;
  key_strengths: string[];
  recommendations: Recommendation[];
  quick_win: QuickWin | null;
  data_quality_note: string | null;
}

interface ActionPlanResponse {
  session_id: string;
  success: boolean;
  result: ActionPlanResult | null;
  health_score: number;
  health_label: string;
  provider: string | null;
  error: string | null;
}

// ── Report / Export ───────────────────────────────────────────────────
// GET /report/{session_id} → 200: application/pdf binary
// GET /export/{session_id} → 200: text/csv binary

// ── Health ────────────────────────────────────────────────────────────

interface HealthResponse {
  status: string;         // "ok"
  version: string;
  timestamp: string;      // ISO 8601
  modules: string[];
}
```

---

## Section 5 — Error handling contract

All API errors return JSON with one of these shapes:
```typescript
{ detail: string }
// or for validation errors (422):
{ detail: Array<{ loc: (string | number)[]; msg: string; type: string }> }
```

| HTTP Status | Frontend behaviour |
|---|---|
| **401** | Clear `localStorage`, redirect to `/login` immediately. Do NOT show error UI — just redirect. |
| **403** | Show inline banner: "Access denied. This session belongs to a different account." |
| **404** | Show inline message: "Not found. The session or resource does not exist." |
| **409** | Show inline field error (signup/change-password): "An account with this email already exists." |
| **413** | Show file upload error: "File too large. Maximum supported size is 10 MB." |
| **415** | Show file upload error: "Unsupported file type. Upload a .csv, .xlsx, or .xls file." |
| **422** | Parse `detail` array and show each `msg` next to the relevant field. |
| **425** | Show info banner: "Analysis not ready. Start or wait for the analysis to complete first." |
| **500** | Show full-page error card: generic message + "Try Again" button that retries the last request. |
| Network error | Show toast: "Cannot reach the server. Check your connection and try again." |

---

## Section 6 — Brand design tokens

```css
/* Colours */
--color-primary:        #0F6E56;   /* teal — buttons, links, active states */
--color-primary-dark:   #094D3C;   /* teal dark — hover states, headers */
--color-primary-light:  #E8F5F1;   /* teal light — backgrounds, badges */
--color-error:          #C0392B;   /* red — critical badges, error text */
--color-warning:        #E67E22;   /* amber — medium urgency, warnings */
--color-success:        #27AE60;   /* green — positive sentiment, low urgency */
--color-text:           #4A4A4A;   /* body text */
--color-text-muted:     #888888;   /* captions, placeholders */
--color-border:         #CCCCCC;   /* table borders, input borders */
--color-background:     #FAFAF8;   /* page background */
--color-surface:        #FFFFFF;   /* card backgrounds */

/* Typography */
--font-family:    system-ui, -apple-system, sans-serif;
--font-size-base: 14px;
--line-height:    1.5;

/* Spacing */
--border-radius-card:  8px;
--border-radius-input: 4px;
--border-radius-badge: 4px;

/* Buttons */
/* All primary buttons: background #0F6E56, text white, border-radius 6px, padding 10px 20px */
/* Hover: background #094D3C */
/* Disabled: background #CCCCCC, cursor not-allowed */

/* Tailwind config equivalents */
/* primary: { DEFAULT: '#0F6E56', dark: '#094D3C', light: '#E8F5F1' } */
/* error: '#C0392B', warning: '#E67E22', success: '#27AE60' */
```

---

## Section 7 — Key UX rules the frontend must follow

1. **File column detection.** After a file is selected in `/analyse/upload`, display the auto-detected review column name (returned in the `AnalyseResponse.preprocessing` notes or inferred client-side). Show a dropdown listing all detected column names so the user can override. Do not hide this UI after selection.

2. **Analysis progress bar.** On the Processing screen (`/analyse/processing`): start a fake animation from 0% to 90% over 30 seconds using `setInterval`. When the poll response returns `classification_done: true`, instantly set the bar to 100%, wait 1 second, then navigate to `/results`. Update the displayed `total_classified` count on each successful poll response.

3. **Action plan generate button.** On the Results screen, the "Generate Action Plan" button must show a spinner and be disabled for the entire duration of the `POST /action-plan/{session_id}` request. If the request fails, re-enable the button and show an inline error. If `success` is `false` in the response, show the `error` field as an inline message.

4. **PDF download.** Open the PDF in a **new browser tab** — do NOT trigger a download dialog. Implementation: fetch `GET /report/{session_id}` with the auth header, receive the binary response, create a `Blob` (`new Blob([data], { type: 'application/pdf' })`), create an object URL (`URL.createObjectURL(blob)`), open it with `window.open(url, '_blank')`. Clean up the object URL after 60 s.

5. **CSV download.** Trigger a browser download. Implementation: fetch `GET /export/{session_id}` with the auth header, receive the text response, create a `Blob` (`new Blob([data], { type: 'text/csv' })`), create an object URL, create a hidden `<a>` element with `download="feedbackiq_results.csv"`, click it programmatically, then remove it and revoke the URL.

6. **Session history table.** Displayed on both `/dashboard` and `/account`. Clicking any row navigates to `/results?session={session_id}`. Show columns: Company (from `label`), Date (`created_at` formatted as `DD MMM YYYY`), Reviews (`total_reviews`), Score (`overall_score` with a colour dot). Empty state: "No analyses yet. Start your first analysis →" with a link to `/analyse/profile`.

7. **Profile form — 404 handling.** When `GET /auth/profile` returns 404, render the profile form with all fields empty and no error message. The 404 is expected for new users who have not yet saved a profile.

8. **Auth guard.** Every protected route must check `localStorage.getItem('access_token')` on mount. If null, redirect to `/login` immediately (before any render). Use a `<PrivateRoute>` wrapper component in React Router.

9. **Category tag input.** The categories field (in profile form and session creation) is a tag input: the user types a category name and presses Enter or comma to add it. Show each tag as a removable chip. Enforce 2–8 tags. Show a counter "X / 8 categories added". Warn (but do not block) if two categories share more than 60% of words.

10. **Token storage keys.** Use exactly `access_token` and `refresh_token` as the `localStorage` keys.

---

## Section 8 — Bolt.new prompt to paste

Paste the following prompt verbatim into Bolt.new to generate the frontend skeleton:

---

```
Build a complete React 18 + TypeScript + Tailwind CSS + React Router v6 frontend for FeedbackIQ, a customer feedback intelligence SaaS. Use axios for all API calls. Do NOT use any built-in Bolt database, auth, or backend — all data comes from a FastAPI backend running at http://localhost:8000.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AXIOS SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create src/api/client.ts:

import axios from 'axios';

const api = axios.create({ baseURL: 'http://localhost:8000' });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post('http://localhost:8000/auth/refresh', { refresh_token: refreshToken });
          localStorage.setItem('access_token', data.access_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BRAND COLOURS (add to tailwind.config.js)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

colors: {
  primary: { DEFAULT: '#0F6E56', dark: '#094D3C', light: '#E8F5F1' },
  error:   '#C0392B',
  warning: '#E67E22',
  success: '#27AE60',
  muted:   '#888888',
  border:  '#CCCCCC',
  surface: '#FAFAF8',
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPESCRIPT INTERFACES (src/types/api.ts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface TokenResponse {
  access_token: string; refresh_token: string; token_type: string;
  user_id: string; email: string; full_name: string; has_profile: boolean;
}
export interface UserMeResponse {
  user_id: string; email: string; full_name: string; created_at: string;
  last_login: string | null; profile: ProfileData | null;
  session_count: number; has_profile: boolean;
}
export interface ProfileData {
  company_name: string; industry: string; categories: string[];
  description?: string | null; urgency_definition?: string | null;
}
export interface SessionSummary {
  session_id: string; label: string; created_at: string;
  total_reviews: number; overall_score: number;
}
export interface SessionsListResponse { sessions: SessionSummary[]; total: number; }
export interface CreateSessionResponse {
  session_id: string; profile: ProfileData; created_at: string; user_id?: string | null;
}
export interface PreprocessingSummary {
  input_count: number; final_count: number; noise_removed: number;
  exact_duplicates_removed: number; near_duplicates_removed: number; short_removed: number;
}
export interface AnalyseResponse {
  session_id: string; total_classified: number; total_failed: number;
  gemini_fallback_count: number; failed_batches: unknown[];
  preprocessing: PreprocessingSummary;
}
export interface SentimentData {
  positive_count: number; negative_count: number; neutral_count: number;
  positive_pct: number; negative_pct: number; neutral_pct: number; overall_score: number;
}
export interface CategoryItem { category: string; count: number; pct: number; }
export interface UrgencyData {
  critical_count: number; medium_count: number; low_count: number; critical_pct: number;
}
export interface EmotionItem { emotion: string; count: number; pct: number; }
export interface TopIssue { category: string; count: number; critical_count: number; example: string; }
export interface DashboardData {
  total_reviews: number; sentiment: SentimentData; categories: CategoryItem[];
  urgency: UrgencyData; emotions: EmotionItem[]; top_issues: TopIssue[];
  top_category: string; multi_aspect: { multi_aspect_count: number; multi_aspect_pct: number; single_aspect_count: number };
}
export interface DashboardResponse {
  session_id: string; profile: ProfileData; dashboard_data: DashboardData;
  classification_done: boolean; total_classified: number;
}
export interface Recommendation {
  rank: number; title: string; rationale: string; action: string;
  impact: 'high'|'medium'|'low'; effort: 'high'|'medium'|'low';
  timeframe: 'immediate'|'short_term'|'long_term';
}
export interface ActionPlanResult {
  health_score: number; health_label: string; executive_summary: string;
  key_strengths: string[]; recommendations: Recommendation[];
  quick_win: { title: string; description: string; expected_outcome: string } | null;
  data_quality_note: string | null;
}
export interface ActionPlanResponse {
  session_id: string; success: boolean; result: ActionPlanResult | null;
  health_score: number; health_label: string; provider: string | null; error: string | null;
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUTING (src/App.tsx)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use React Router v6 with these routes:
  /login                  → LoginPage
  /signup                 → SignupPage
  /dashboard              → DashboardPage (private)
  /analyse/profile        → ProfilePage (private)
  /analyse/upload         → UploadPage (private, reads ?session= from URL)
  /analyse/processing     → ProcessingPage (private, reads ?session= from URL)
  /results                → ResultsPage (private, reads ?session= from URL)
  /account                → AccountPage (private)
  /                       → redirect to /dashboard

PrivateRoute: check localStorage.getItem('access_token'); if null redirect to /login.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN 1 — LoginPage (/login)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Centered card (max-w-md, rounded-lg border border-border bg-white shadow-sm p-8).
Header: "FeedbackIQ" in text-primary font-bold text-2xl.
Subheader: "Sign in to your account" text-muted.
Fields: Email (type email), Password (type password).
Button: "Log In" full-width bg-primary text-white rounded-md py-2.5.
Link below: "Don't have an account? Sign up" → /signup.

API: POST /auth/login as URLSearchParams { username: email, password }.
On 200: store access_token + refresh_token, navigate to /dashboard.
On 401: show "Invalid email or password" below the form.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN 2 — SignupPage (/signup)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Same card layout as login.
Fields: Full Name, Email, Password (min 8 chars).
Button: "Create Account".
Link: "Already have an account? Log in" → /login.

API: POST /auth/signup JSON { email, password, full_name }.
On 201: store tokens, navigate to /dashboard.
On 409: show "An account with this email already exists."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN 3 — DashboardPage (/dashboard)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Top navbar: FeedbackIQ logo left, user full_name chip right with logout button.
Page: heading "Your Analyses". Button "New Analysis →" links to /analyse/profile.
Below: table with columns [Company, Date, Reviews, Score].
  - Populate from GET /sessions.
  - Each row clickable → navigate to /results?session={session_id}.
  - Empty state: "No analyses yet. Click New Analysis to start."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN 4 — ProfilePage (/analyse/profile)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

On mount: GET /auth/profile. On 200 pre-fill fields. On 404 show empty form.
Two-column grid form:
  Left: Company Name (required), Industry (required), Description (textarea, optional).
  Right: Categories (tag input — type + Enter to add, 2–8 tags), Urgency Definition (textarea, optional).
Checkbox: "Save this profile for next time".
Button: "Next →" (primary).

On submit:
  1. If checkbox checked: PUT /auth/profile with form values.
  2. POST /sessions with { company_name, industry, categories, description, urgency_definition }.
  3. On 201: navigate to /analyse/upload?session={session_id}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN 5 — UploadPage (/analyse/upload?session=)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read session_id from URL search params.
Two tabs: "Paste Text" | "Upload File".

Paste tab: large textarea (min-h-48), label "One review per line or separated by double newline."
  Button "Run Analysis" → POST /analyse/text as URLSearchParams { session_id, raw_text }.

File tab: drag-and-drop zone (dashed border, rounded, text "Drop a CSV or Excel file here").
  After file chosen: show file name + a "Review column" dropdown (pre-filled with auto-detected name).
  Button "Run Analysis" → POST /analyse/file as FormData { session_id, file, column }.

On 200 from either: navigate to /analyse/processing?session={session_id}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN 6 — ProcessingPage (/analyse/processing?session=)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Centered card. Heading "Classifying your reviews…".
Animated progress bar (bg-primary). Fake progress: 0→90% over 30s via setInterval(100ms).
Counter: "X reviews classified" updated from each poll response.

Poll GET /dashboard/{session_id} every 3000ms.
When classification_done === true: set progress to 100%, wait 1s, navigate to /results?session={session_id}.
Clear the poll interval on component unmount.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN 7 — ResultsPage (/results?session=)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

On mount: GET /dashboard/{session_id}.

Layout:
  Back arrow → /dashboard.
  Heading: company_name from profile.
  Metric cards row (4 cards): Total Reviews, Positive %, Critical Issues, Overall Score.
    Score card colour: green if ≥75, amber if ≥50, red if <50.
  
  Charts section: placeholder divs for Sentiment (pie), Emotions (bar), Categories (bar).
    Label each placeholder with its chart name in text-muted.
  
  Issues table: columns [Rank, Category, Negative Reviews, Critical, Example Feedback].
    Populate from dashboard_data.top_issues.
  
  Action Plan panel:
    Button "Generate Action Plan" (bg-primary text-white). On click:
      - Disable button, show spinner inside it.
      - POST /action-plan/{session_id}.
      - On 200 with success=true: show health score banner (coloured by label) + recommendations cards.
      - Each rec card: title, impact/effort/timeframe badges, rationale (italic), action text.
      - On failure: re-enable button, show error message.
  
  Download row: two buttons side by side.
    "Download PDF" (outline): fetch /report/{session_id} → Blob → window.open(blobUrl, '_blank').
    "Export CSV" (outline): fetch /export/{session_id} → Blob → trigger <a download> click.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN 8 — AccountPage (/account)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

On mount: GET /auth/me (user info), GET /auth/history (session list).

Layout:
  User info header: full name, email, joined date, session count.
  
  Two panels side by side:
    Panel 1 — "Company Profile":
      Same form as ProfilePage.
      Pre-fill from UserMeResponse.profile (or empty if null).
      "Save Profile" button → PUT /auth/profile.
      On 200: show success toast "Profile saved."
    
    Panel 2 — "Change Password":
      Fields: Current Password, New Password (min 8).
      "Update Password" button → POST /auth/change-password.
      On 200: show success toast "Password updated." Clear fields.
      On 401: show "Current password is incorrect."
  
  Below: "Analysis History" table → same as /dashboard table, populated from GET /auth/history.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ERROR HANDLING (global)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create an error handling utility. For every API error:
  401 → clear localStorage, window.location.href = '/login'
  403 → show banner "Access denied."
  404 → show inline "Not found."
  422 → parse error.response.data.detail array, show each msg near the relevant field
  425 → show "Analysis not ready. Please wait for classification to complete."
  500 → show full-page error with "Try Again" button

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADDITIONAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Use React Query (or useState/useEffect) for all data fetching.
- All primary buttons: class "bg-primary hover:bg-primary-dark text-white font-medium rounded-md px-4 py-2.5 transition-colors".
- All input fields: class "w-full border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary".
- All cards: class "bg-white rounded-lg border border-border shadow-sm p-6".
- Page background: bg-surface (#FAFAF8).
- Font: system-ui, sans-serif (Tailwind default font-sans is fine).
- Mobile-responsive: all layouts should work on screens ≥ 375px wide.
- No mock auth, no Bolt DB, no Supabase — every call goes to http://localhost:8000.
```

---

*End of FeedbackIQ Frontend Handoff Document.*
