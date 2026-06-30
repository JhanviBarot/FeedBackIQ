import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from core.preprocessing import preprocess, batch_reviews
from core.prompt_builder import build_prompt_pair
from core.classifier import classify_all_batches
from streamlit_ui.style import CUSTOM_CSS
from core.aggregator import build_dashboard_data
from core.charts import (
    build_sentiment_donut,
    build_emotion_bar,
    build_category_bar,
    build_urgency_heatmap,
    build_aspect_summary,
)
from core.file_input import (
    parse_uploaded_file,
    detect_review_column,
    extract_review_lines,
    lines_to_raw_text,
)
from core.action_plan import generate_action_plan, compute_health_score
from core.pdf_report import generate_pdf
from datetime import datetime
from api.auth.password import hash_password, verify_password
from api.auth.tokens import create_access_token
from api.storage.users import UserStore

INDUSTRIES = [
    "E-commerce",
    "SaaS",
    "Hospitality",
    "Retail",
    "Logistics",
    "Other",
]

def categories_too_similar(cat1: str, cat2: str) -> bool:
    words1 = set(cat1.lower().split())
    words2 = set(cat2.lower().split())
    if not words1 or not words2:
        return False
    overlap = len(words1 & words2)
    smaller = min(len(words1), len(words2))
    return (overlap / smaller) >= 0.6


def validate_categories(categories: list) -> str | None:
    for i in range(len(categories)):
        for j in range(i + 1, len(categories)):
            if categories_too_similar(categories[i], categories[j]):
                return (
                    f'"{categories[i]}" and "{categories[j]}" are too similar. '
                    f"Please make your categories more distinct."
                )
    return None


def format_aspects(aspects: list) -> str:
    if not aspects:
        return ""
    lines = []
    for a in aspects:
        emoji_map = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}
        icon = emoji_map.get(a["sentiment"], "⚪")
        lines.append(f"{icon} {a['category']} → {a['sentiment']}")
    return "\n".join(lines)

def build_results_dataframe(all_results: list, reviews: list) -> pd.DataFrame:
    review_map = {r["id"]: r["text"] for r in reviews}

    rows = []
    for result in all_results:
        rows.append(
            {
                "ID": result["id"],
                "Review": review_map.get(result["id"], ""),
                "Sentiment": result["sentiment"],
                "Primary Category": result["primary_category"],
                "Secondary Category": result.get("secondary_category") or "—",
                "Aspect Breakdown": format_aspects(result.get("aspects", [])),
                "Urgency": result["urgency"],
                "Emotion": result["emotion"],
                "Core Issue": result["core_issue"],
                "Confidence": result["confidence"],
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("ID").reset_index(drop=True)
    return df

def show_profile_setup():
    st.title("FeedbackIQ")
    st.write("Before analysing feedback, tell us about your company.")
    st.divider()

    company_name = st.text_input("Company name *", placeholder="e.g. FreshBites")

    industry = st.selectbox("Industry *", options=["-- Select --"] + INDUSTRIES)

    st.write("Custom categories * (minimum 2, maximum 8)")
    st.caption(
        "Define the categories that matter to your business. "
        "Reviews will be classified into these exact categories. "
        "A built-in 'General Experience' category is always available as a fallback."
    )

    num_categories = st.number_input(
        "How many categories?", min_value=2, max_value=8, value=4, step=1
    )

    categories = []
    for i in range(int(num_categories)):
        cat = st.text_input(
            f"Category {i + 1}", key=f"cat_{i}", placeholder="e.g. Delivery Speed"
        )
        if cat.strip():
            categories.append(cat.strip())

    description = st.text_area(
        "Company description (optional)",
        placeholder="e.g. We are a cloud kitchen delivering meals in Ahmedabad.",
        height=80,
    )

    urgency_definition = st.text_input(
        "What does 'critical' urgency mean for your business? (optional)",
        placeholder="e.g. Customer threatened to never return or mentioned food safety concerns.",
    )

    if st.button("Save Profile and Continue", type="primary"):
        if not company_name.strip():
            st.error("Company name is required.")
            return

        if industry == "-- Select --":
            st.error("Please select your industry.")
            return

        if len(categories) < 2:
            st.error(
                f"Please fill in at least 2 categories. "
                f"You have filled {len(categories)} so far."
            )
            return

        category_error = validate_categories(categories)
        if category_error:
            st.error(category_error)
            return

        st.session_state["profile"] = {
            "company_name": company_name.strip(),
            "industry": industry,
            "categories": categories,
            "description": description.strip() or None,
            "urgency_definition": urgency_definition.strip() or None,
        }

        st.rerun()

def handle_file_upload(uploaded_file) -> str:
    parsed = parse_uploaded_file(uploaded_file, filename=uploaded_file.name)

    if parsed["error"]:
        st.error(parsed["error"])
        return ""

    if parsed["detected_column"] and parsed["raw_text_lines"]:
        st.success(
            f"Detected review column: **{parsed['detected_column']}** "
            f"({len(parsed['raw_text_lines'])} rows found)"
        )

        override = st.checkbox(
            "Use a different column instead", key=f"override_{uploaded_file.name}"
        )

        if override:
            chosen_column = st.selectbox(
                "Select the correct review column",
                options=parsed["columns"],
                key=f"col_select_{uploaded_file.name}",
            )
            extraction = extract_review_lines(parsed["dataframe"], chosen_column)
            if extraction["error"]:
                st.error(extraction["error"])
                return ""
            return lines_to_raw_text(extraction["raw_text_lines"])

        return lines_to_raw_text(parsed["raw_text_lines"])

    else:
        st.warning("Could not auto-detect a review column. Please select one below.")
        chosen_column = st.selectbox(
            "Select the column containing review text",
            options=parsed["columns"],
            key=f"col_manual_{uploaded_file.name}",
        )
        extraction = extract_review_lines(parsed["dataframe"], chosen_column)
        if extraction["error"]:
            st.error(extraction["error"])
            return ""
        return lines_to_raw_text(extraction["raw_text_lines"])

def show_main_app():
    profile = st.session_state["profile"]

    st.title("FeedbackIQ")
    st.caption(
        f"Analysing feedback for **{profile['company_name']}** · {profile['industry']}"
    )

    with st.sidebar:
        st.subheader(profile["company_name"])
        st.caption(profile["industry"])
        st.caption(f"{len(profile['categories'])} custom categories")

        if st.button("Change company profile"):
            for key in [
                "profile",
                "results_df",
                "classification_done",
                "failed_batches",
                "action_plan",
                "action_plan_loading",
            ]:
                st.session_state.pop(key, None)
            st.rerun()

        st.divider()

        input_tab1, input_tab2, input_tab3 = st.tabs(
            ["Paste Text", "Upload CSV", "Upload Excel"]
        )

        raw_text = ""

        with input_tab1:
            pasted_text = st.text_area(
                "Paste customer reviews — one per line",
                height=240,
                placeholder=(
                    "The delivery was late and packaging was damaged.\n"
                    "Excellent product, arrived on time.\n"
                    "Customer support never responded to my complaint."
                ),
            )
            if pasted_text.strip():
                raw_text = pasted_text

        with input_tab2:
            csv_file = st.file_uploader(
                "Upload a CSV file", type=["csv"], key="csv_uploader"
            )
            if csv_file:
                raw_text = handle_file_upload(csv_file)

        with input_tab3:
            excel_file = st.file_uploader(
                "Upload an Excel file", type=["xlsx", "xls"], key="excel_uploader"
            )
            if excel_file:
                raw_text = handle_file_upload(excel_file)

        analyse_clicked = st.button(
            "Analyse Feedback", type="primary", use_container_width=True
        )

    if analyse_clicked:
        if not raw_text.strip():
            st.error("Please paste at least one review before clicking Analyse.")
            return

        for key in ["results_df", "classification_done", "failed_batches",
                    "action_plan", "action_plan_loading"]:
            st.session_state.pop(key, None)

        result = preprocess(raw_text)

        if result["error"]:
            st.error(result["error"])
            return

        report = result["report"]
        reviews = result["reviews"]

        st.success(
            f"Preprocessing complete — "
            f"{report['final_count']} reviews ready for analysis."
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Received", report["input_count"])
        col2.metric("Noise removed", report["noise_removed"])
        col3.metric(
            "Duplicates removed",
            report["exact_duplicates_removed"] + report["near_duplicates_removed"],
        )
        col4.metric("Analysing", report["final_count"])

        batches = batch_reviews(reviews)

        total_batches = len(batches)

        st.write(
            f"Sending **{report['final_count']} reviews** "
            f"across **{total_batches} batch(es)** to Groq."
        )

        progress_bar = st.progress(0)
        status_text = st.empty()
        live_metrics = st.empty()

        def update_progress(summary: dict):
            pct = summary["pct_complete"] / 100
            progress_bar.progress(pct)

            status_text.caption(
                f"Batch {summary['completed_batches']} of {summary['total_batches']} complete "
                f"· {summary['classified_so_far']} reviews classified"
                + (
                    f" · {summary['failed_count']} failed"
                    if summary["failed_count"] > 0
                    else ""
                )
            )

            with live_metrics.container():
                lm1, lm2, lm3 = st.columns(3)
                lm1.metric("Classified so far", summary["classified_so_far"])
                lm2.metric("Positive so far", summary["positive_so_far"])
                lm3.metric("Critical so far", summary["critical_so_far"])

        classification = classify_all_batches(
            batches, profile, progress_callback=update_progress
        )

        progress_bar.progress(1.0)
        status_text.caption("Classification complete.")
        live_metrics.empty()

        if classification["total_classified"] == 0:
            st.error(
                "Classification failed for all batches. "
                "Check your Groq API key in the .env file."
            )
            return

        df = build_results_dataframe(classification["all_results"], reviews)
        st.session_state["results_df"] = df
        st.session_state["failed_batches"] = classification["failed_batches"]
        st.session_state["classification_done"] = True

    if st.session_state.get("classification_done"):
        df = st.session_state["results_df"]
        failed_batches = st.session_state["failed_batches"]

        dashboard_data = build_dashboard_data(df)

        st.divider()
        st.subheader(f"Feedback Intelligence — {profile['company_name']}")

        sentiment_score = dashboard_data["sentiment"]["overall_score"]
        score_label = (
            "Strong"
            if sentiment_score >= 70
            else "Mixed"
            if sentiment_score >= 40
            else "Concerning"
        )

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Reviews Analysed", dashboard_data["total_reviews"])

        m2.metric(
            "Overall Sentiment",
            f"{sentiment_score}%",
            delta=score_label,
            delta_color="off",
        )

        m3.metric(
            "Critical Issues",
            dashboard_data["urgency"]["critical_count"],
            delta=f"{dashboard_data['urgency']['critical_pct']}% of total"
            if dashboard_data["urgency"]["critical_count"] > 0
            else None,
            delta_color="inverse",
        )

        m4.metric("Top Category", dashboard_data["top_category"])

        if failed_batches:
            st.caption(
                f"⚠️ {sum(len(b['batch_ids']) for b in failed_batches)} review(s) "
                f"could not be classified after retries."
            )

        st.write("")
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("**Sentiment Distribution**")
            st.plotly_chart(
                build_sentiment_donut(dashboard_data["sentiment"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        with chart_col2:
            st.markdown("**Emotion Breakdown**")
            st.plotly_chart(
                build_emotion_bar(dashboard_data["emotions"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        st.write("")
        chart_col3, chart_col4 = st.columns(2)

        with chart_col3:
            st.markdown(f"**Feedback by {profile['company_name']}'s Categories**")
            st.plotly_chart(
                build_category_bar(dashboard_data["categories"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        with chart_col4:
            st.markdown("**Urgency Matrix — Where to Act First**")
            st.plotly_chart(
                build_urgency_heatmap(dashboard_data["urgency_matrix"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        st.write("")
        st.markdown(
            f"**Issue Complexity** · {dashboard_data['multi_aspect']['multi_aspect_pct']}% of reviews mention more than one issue"
        )
        st.plotly_chart(
            build_aspect_summary(df),
            use_container_width=True,
            config={"displayModeBar": False},
        )

        if dashboard_data["top_issues"]:
            st.write("")
            st.markdown("**Where to Focus — Top Negative Issue Areas**")
            for issue in dashboard_data["top_issues"]:
                critical_flag = (
                    f" · {issue['critical_count']} critical"
                    if issue["critical_count"] > 0
                    else ""
                )
                st.markdown(
                    f"- **{issue['category']}** — {issue['count']} negative review(s){critical_flag}  \n"
                    f'  _e.g. "{issue["example"]}"_'
                )
        else:
            st.write("")
            st.success("No significant negative issue areas detected.")

        # ── Health Score Badge (Python-computed, zero LLM cost) ──────────────
        st.divider()

        health_score, health_label = compute_health_score(dashboard_data)

        if health_score >= 75:
            badge_color = "green"
        elif health_score >= 50:
            badge_color = "#e6a817"
        elif health_score >= 25:
            badge_color = "#e07000"
        else:
            badge_color = "#c0392b"

        st.markdown(
            f"""<div style="display:inline-flex;align-items:center;gap:12px;
                padding:10px 18px;border-radius:8px;
                background-color:{badge_color}22;border:1px solid {badge_color}66;">
              <span style="font-size:2rem;font-weight:700;color:{badge_color};">
                {health_score}
              </span>
              <span style="font-size:1rem;color:{badge_color};font-weight:600;">
                / 100 &nbsp;—&nbsp; {health_label}
              </span>
              <span style="font-size:0.8rem;color:#888;margin-left:6px;">
                Customer Health Score
              </span>
            </div>""",
            unsafe_allow_html=True,
        )

        st.write("")

        # ── Action Plan Section ───────────────────────────────────────────────
        action_plan_col, _ = st.columns([2, 3])

        with action_plan_col:
            generate_clicked = st.button(
                "✦ Generate AI Action Plan",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.get("action_plan_loading", False),
            )

        if generate_clicked:
            st.session_state["action_plan_loading"] = True
            st.session_state.pop("action_plan", None)

            with st.spinner("Generating action plan…"):
                plan = generate_action_plan(dashboard_data, profile)

            st.session_state["action_plan"] = plan
            st.session_state["action_plan_loading"] = False
            st.rerun()

        if st.session_state.get("action_plan"):
            plan = st.session_state["action_plan"]

            if not plan["success"]:
                st.error(
                    f"Action plan generation failed: {plan['error']}. "
                    f"Try clicking Generate again."
                )
            else:
                result = plan["result"]

                provider_label = (
                    f" · via {plan['provider'].capitalize()}"
                    if plan.get("provider")
                    else ""
                )
                st.caption(f"Action plan generated{provider_label}")

                # Executive Summary
                st.markdown("#### Executive Summary")
                st.markdown(result["executive_summary"])

                # Key Strengths
                if result["key_strengths"]:
                    st.markdown("#### What's Working")
                    for strength in result["key_strengths"]:
                        st.markdown(f"- {strength}")

                # Recommendations
                st.markdown("#### Recommendations")

                _IMPACT_COLORS = {"high": "#c0392b", "medium": "#e07000", "low": "#27ae60"}
                _EFFORT_COLORS = {"low": "#27ae60", "medium": "#e07000", "high": "#c0392b"}
                _TIME_COLORS = {
                    "immediate": "#c0392b",
                    "short_term": "#e07000",
                    "long_term": "#2980b9",
                }

                def _badge(label: str, color: str) -> str:
                    return (
                        f'<span style="background:{color}22;color:{color};'
                        f'border:1px solid {color}66;border-radius:4px;'
                        f'padding:1px 7px;font-size:0.75rem;font-weight:600;'
                        f'margin-left:4px;">{label.upper().replace("_"," ")}</span>'
                    )

                for rec in result["recommendations"]:
                    impact_badge = _badge(rec["impact"], _IMPACT_COLORS[rec["impact"]])
                    effort_badge = _badge(f"{rec['effort']} effort", _EFFORT_COLORS[rec["effort"]])
                    time_badge = _badge(rec["timeframe"], _TIME_COLORS[rec["timeframe"]])

                    st.markdown(
                        f"**{rec['rank']}. {rec['title']}** "
                        f"{impact_badge}{effort_badge}{time_badge}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"_{rec['rationale']}_")
                    st.markdown(rec["action"])
                    st.write("")

                # Quick Win
                st.markdown("#### Quick Win This Week")
                st.info(
                    f"**{result['quick_win']['title']}**\n\n"
                    f"{result['quick_win']['description']}\n\n"
                    f"_Expected: {result['quick_win']['expected_outcome']}_"
                )

                # Data quality warning
                if result.get("data_quality_note"):
                    st.warning(result["data_quality_note"])

                # Regenerate button
                if st.button("↺ Regenerate Action Plan", type="secondary"):
                    st.session_state.pop("action_plan", None)
                    st.rerun()

        st.divider()
        st.subheader("Full Results")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Review": st.column_config.TextColumn(width="large"),
                "Aspect Breakdown": st.column_config.TextColumn(width="medium"),
                "Core Issue": st.column_config.TextColumn(width="medium"),
            },
        )

        if failed_batches:
            st.warning(
                f"{len(failed_batches)} batch(es) failed after all retry attempts."
            )
            with st.expander("See failed batch details"):
                for fb in failed_batches:
                    st.write(
                        f"Batch {fb['batch_number']} "
                        f"(Review IDs: {fb['batch_ids']}): {fb['error']}"
                    )

        st.markdown("---")
        st.subheader("Download Report")

        col_pdf, col_csv = st.columns([1, 1])

        with col_pdf:
            if st.session_state.get("classification_done"):
                if st.button("📄 Download PDF Report", use_container_width=True):
                    with st.spinner("Generating PDF report..."):
                        try:
                            pdf_bytes = generate_pdf(
                                dashboard_data=build_dashboard_data(
                                    st.session_state["results_df"]
                                ),
                                action_plan=st.session_state.get(
                                    "action_plan",
                                    {
                                        "success": False,
                                        "result": None,
                                        "health_score": 0,
                                        "health_label": "—",
                                        "error": "Not generated",
                                    },
                                ),
                                profile=st.session_state["profile"],
                                results_df=st.session_state["results_df"],
                            )
                            st.download_button(
                                label="⬇ Click to Save PDF",
                                data=pdf_bytes,
                                file_name=f"feedbackiq_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
                        except RuntimeError as e:
                            st.error(f"PDF generation failed: {e}")
            else:
                st.info("Run an analysis first to generate the PDF report.")

        with col_csv:
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Results as CSV",
                data=csv_data,
                file_name=(
                    f"{profile['company_name'].replace(' ', '_')}_feedbackiq_results.csv"
                ),
                mime="text/csv",
                use_container_width=True,
            )


def show_auth_screen():
    st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1rem 0'>
            <h1 style='color:#0F6E56; font-size:2.2rem; margin:0'>
                📊 FeedbackIQ
            </h1>
            <p style='color:#666; font-size:1rem; margin-top:0.25rem'>
                Customer Feedback Intelligence Platform
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["Log In", "Create Account"])

    with tab_login:
        st.markdown("#### Welcome back")
        email_in = st.text_input("Email", key="login_email",
                                  placeholder="you@company.com")
        pass_in = st.text_input("Password", type="password",
                                 key="login_pass")
        login_btn = st.button("Log In", use_container_width=True,
                              type="primary")
        if login_btn:
            if not email_in or not pass_in:
                st.error("Please enter both email and password.")
            else:
                store = UserStore()
                user = store.get_user_by_email(email_in)
                if user and verify_password(pass_in, user["hashed_password"]):
                    store.update_last_login(user["user_id"])
                    st.session_state["auth_mode"] = "app"
                    st.session_state["auth_user"] = user
                    st.session_state["auth_token"] = create_access_token(
                        user["user_id"], user["email"])
                    if user.get("profile"):
                        st.session_state["profile"] = user["profile"]
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    with tab_signup:
        st.markdown("#### Create your account")
        name_in = st.text_input("Full name", key="signup_name",
                                  placeholder="Jane Smith")
        email_s = st.text_input("Email", key="signup_email",
                                  placeholder="jane@company.com")
        pass_s = st.text_input("Password (min 8 characters)",
                                 type="password", key="signup_pass")
        pass_c = st.text_input("Confirm password",
                                 type="password", key="signup_confirm")
        signup_btn = st.button("Create Account", use_container_width=True,
                                type="primary")
        if signup_btn:
            errors = []
            if not name_in.strip():
                errors.append("Full name is required.")
            if not email_s.strip():
                errors.append("Email is required.")
            if len(pass_s) < 8:
                errors.append("Password must be at least 8 characters.")
            if pass_s != pass_c:
                errors.append("Passwords do not match.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                store = UserStore()
                if store.email_exists(email_s):
                    st.error("An account with this email already exists.")
                else:
                    try:
                        user = store.create_user(
                            email=email_s,
                            hashed_password=hash_password(pass_s),
                            full_name=name_in.strip(),
                        )
                        st.session_state["auth_mode"] = "app"
                        st.session_state["auth_user"] = user
                        st.session_state["auth_token"] = create_access_token(
                            user["user_id"], user["email"])
                        st.success("Account created! Setting up...")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    st.markdown("---")
    if st.button("Continue as Guest (no account required)",
                 use_container_width=True):
        st.session_state["auth_mode"] = "guest"
        st.rerun()

    st.markdown("""
        <div style='text-align:center; margin-top:1rem;
                    color:#999; font-size:0.8rem'>
            Your data is never shared. Analyses are saved to your
            account when logged in.
        </div>
    """, unsafe_allow_html=True)


def show_user_profile_page():
    user = st.session_state.get("auth_user", {})
    st.markdown(f"### 👤 {user.get('full_name', 'Your Account')}")
    st.caption(user.get("email", ""))
    if st.button("← Back to Analysis"):
        del st.session_state["show_profile_page"]
        st.rerun()
    st.markdown("---")
    tab_info, tab_history = st.tabs(["Account & Profile", "Analysis History"])

    with tab_info:
        st.markdown("#### Saved Company Profile")
        profile = user.get("profile")
        if profile:
            st.write(f"**Company:** {profile.get('company_name')}")
            st.write(f"**Industry:** {profile.get('industry')}")
            st.write(f"**Categories:** "
                     f"{', '.join(profile.get('categories', []))}")
            if st.button("Edit Profile"):
                if "profile" in st.session_state:
                    del st.session_state["profile"]
                del st.session_state["show_profile_page"]
                st.rerun()
        else:
            st.info("No company profile saved yet.")
        st.markdown("---")
        st.markdown("#### Change Password")
        cur_p = st.text_input("Current password", type="password",
                               key="cp_cur")
        new_p = st.text_input("New password (min 8 chars)", type="password",
                               key="cp_new")
        if st.button("Change Password"):
            if len(new_p) < 8:
                st.error("New password must be at least 8 characters.")
            elif verify_password(cur_p, user.get("hashed_password", "")):
                store = UserStore()
                store.change_password(user["user_id"], hash_password(new_p))
                st.session_state["auth_user"] = store.get_user(user["user_id"])
                st.success("Password changed successfully.")
            else:
                st.error("Current password is incorrect.")

    with tab_history:
        store = UserStore()
        fresh_user = store.get_user(user.get("user_id", ""))
        history = (fresh_user or {}).get("session_history", [])
        if not history:
            st.info("No past analyses yet. Run your first analysis to "
                    "see history here.")
        else:
            st.markdown(f"**{len(history)} past analyses**")
            for item in history:
                cols = st.columns([3, 1, 1])
                cols[0].write(item.get("label", "Analysis"))
                cols[1].write(f"Score: **{item.get('overall_score', '—')}**")
                cols[2].write(f"{item.get('total_reviews', '—')} reviews")


def _get_header_bar():
    user = st.session_state.get("auth_user", {})
    mode = st.session_state.get("auth_mode", "guest")
    if mode == "app" and user:
        cols = st.columns([5, 1, 1])
        cols[0].caption(
            f"👤 **{user.get('full_name', '')}** · {user.get('email', '')}")
        if cols[1].button("Profile"):
            st.session_state["show_profile_page"] = True
            st.rerun()
        if cols[2].button("Log Out"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    elif mode == "guest":
        cols = st.columns([5, 1])
        cols[0].caption("👤 Guest mode — analyses not saved")
        if cols[1].button("Sign In"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# ── ENTRY POINT ───────────────────────────────────────────────────────
st.set_page_config(page_title="FeedbackIQ", page_icon="📊", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

auth_mode = st.session_state.get("auth_mode")

if not auth_mode:
    show_auth_screen()
elif st.session_state.get("show_profile_page"):
    _get_header_bar()
    show_user_profile_page()
elif "profile" not in st.session_state:
    _get_header_bar()
    show_profile_setup()
else:
    _get_header_bar()
    show_main_app()