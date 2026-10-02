# modules/theme.py
# Custom visual theme for StudentStay Colombo.
# Injects fonts + CSS to restyle Streamlit's default components.

import streamlit as st


def inject_custom_css():
    st.markdown(
        """
        <style>
        /* ---------- Fonts ---------- */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, h4,
        .stTabs [data-baseweb="tab"] p,
        div[data-testid="stMetricValue"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        /* ---------- Color palette ---------- */
        :root {
            --forest-darkest: #0d1b12;
            --forest-dark:    #15291c;
            --forest:         #1f4530;
            --forest-mid:     #2f6b45;
            --sage:           #8fbf9f;
            --sage-light:     #e4efe6;
            --amber:          #e0a63d;
            --amber-light:    #f3c878;
            --cream:          #f6f4ec;
            --card-bg:        #ffffff;
            --text-dark:      #142018;
            --text-muted:     #5c6b61;
            --line:           #e2e6de;

            /* StudentStay teal palette */
            --teal-dark:      #082f3a;
            --teal:           #0b5f68;
            --teal-mid:       #087f83;
            --teal-light:     #dff3f1;
            --aqua:            #a8eee8;
            --coral:           #ff9b72;
        }

        /* ---------- Overall app background ---------- */
        .stApp {
            background:
                radial-gradient(
                    circle at 8% 0%,
                    rgba(63, 170, 171, 0.12),
                    transparent 38%
                ),
                radial-gradient(
                    circle at 92% 10%,
                    rgba(255, 166, 104, 0.08),
                    transparent 32%
                ),
                linear-gradient(
                    180deg,
                    #edf6f5 0%,
                    #f5f7f5 34%,
                    #f7f6f1 100%
                );
        }

        /* ---------- Headings & body text ---------- */
        h1, h2, h3 {
            color: var(--forest-dark);
            font-weight: 700 !important;
            letter-spacing: -0.01em;
        }

        /* IMPORTANT: avoid a blanket div/span color rule because it can
           override custom HTML such as the hero banner. */
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {
            color: var(--text-dark);
        }

        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label {
            color: var(--text-dark);
        }

        .stCaption,
        [data-testid="stCaptionContainer"] {
            color: var(--text-muted) !important;
        }

        /* ---------- StudentStay Hero ---------- */
        .ss-hero {
            position: relative;
            overflow: hidden;
            background:
                radial-gradient(
                    circle at 88% 18%,
                    rgba(78, 201, 196, 0.30),
                    transparent 30%
                ),
                radial-gradient(
                    circle at 72% 100%,
                    rgba(255, 166, 104, 0.16),
                    transparent 35%
                ),
                linear-gradient(
                    125deg,
                    #082f3a 0%,
                    #0b4f5c 48%,
                    #087f83 100%
                );
            padding: 42px 42px 44px 42px;
            border-radius: 24px;
            margin-bottom: 22px;
            box-shadow: 0 12px 32px rgba(8, 47, 58, 0.22);
            border: 1px solid rgba(255,255,255,0.10);
        }

        .ss-hero::after {
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            right: -70px;
            top: -90px;
            border-radius: 50%;
            background: rgba(255,255,255,0.07);
            pointer-events: none;
        }

        .ss-hero,
        .ss-hero * {
            color: #ffffff !important;
        }

        .ss-hero-label {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: #a8eee8 !important;
            margin-bottom: 13px;
        }

        .ss-hero-title {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 2.7rem;
            font-weight: 800;
            line-height: 1.08;
            letter-spacing: -0.035em;
            color: #ffffff !important;
            margin: 0;
        }

        .ss-hero-tagline {
            font-family: 'Inter', sans-serif;
            font-size: 1.12rem;
            font-weight: 500;
            line-height: 1.6;
            color: rgba(255,255,255,0.88) !important;
            margin-top: 12px;
            max-width: 650px;
        }

        .ss-hero-support {
            font-family: 'Inter', sans-serif;
            font-size: 0.86rem;
            font-weight: 500;
            color: rgba(255,255,255,0.65) !important;
            margin-top: 18px;
        }

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--forest-darkest) 0%, var(--forest-dark) 100%);
        }

        section[data-testid="stSidebar"] * {
            color: var(--cream) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stExpander"] {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.12);
        }

        /* ---------- Buttons ---------- */
        .stButton > button {
            background: var(--forest-mid);
            color: white;
            border: none;
            border-radius: 999px;
            padding: 10px 26px;
            font-weight: 600;
            font-family: 'Plus Jakarta Sans', sans-serif;
            letter-spacing: 0.01em;
            box-shadow: 0 3px 10px rgba(31, 69, 48, 0.18);
            transition: all 0.2s ease;
        }

        .stButton > button:hover {
            background: var(--amber);
            color: var(--forest-darkest);
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(224, 166, 61, 0.3);
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--amber), var(--amber-light));
            color: var(--forest-darkest);
        }

        .stButton > button[kind="primary"]:hover {
            background: var(--forest-mid);
            color: white;
        }

        .stFormSubmitButton > button {
            background: linear-gradient(135deg, var(--forest), var(--forest-mid));
            color: white;
            border-radius: 999px;
            font-weight: 700;
            font-family: 'Plus Jakarta Sans', sans-serif;
            padding: 12px 30px;
            border: none;
            box-shadow: 0 4px 14px rgba(31, 69, 48, 0.25);
        }

        .stFormSubmitButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(31, 69, 48, 0.35);
        }

        /* ---------- Metrics ---------- */
        div[data-testid="stMetric"] {
            background: var(--card-bg);
            border-radius: 18px;
            padding: 20px 22px;
            border: 1px solid var(--line);
            box-shadow: 0 4px 16px rgba(31, 69, 48, 0.07);
            transition: transform 0.2s ease;
        }

        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 22px rgba(31, 69, 48, 0.12);
        }

        div[data-testid="stMetricValue"] {
            color: var(--forest) !important;
            font-weight: 800 !important;
            font-size: 1.9rem !important;
        }

        div[data-testid="stMetricLabel"] {
            color: var(--text-muted) !important;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.72rem !important;
            letter-spacing: 0.05em;
        }

        /* ---------- Tabs ---------- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background: var(--card-bg);
            padding: 7px;
            border-radius: 16px;
            border: 1px solid var(--line);
            box-shadow: 0 2px 10px rgba(31, 69, 48, 0.05);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 11px;
            padding: 10px 18px;
            color: var(--text-muted) !important;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .stTabs [data-baseweb="tab"] p {
            color: inherit !important;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background: var(--sage-light);
            color: var(--forest-dark) !important;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, var(--forest), var(--forest-mid)) !important;
            color: white !important;
            box-shadow: 0 3px 10px rgba(31, 69, 48, 0.25);
        }

        .stTabs [aria-selected="true"] p {
            color: white !important;
        }

        /* ---------- Expanders ---------- */
        div[data-testid="stExpander"] {
            background: var(--card-bg);
            border-radius: 16px;
            border: 1px solid var(--line);
            box-shadow: 0 2px 10px rgba(31, 69, 48, 0.05);
        }

        div[data-testid="stExpander"] summary {
            font-weight: 600;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        /* ---------- Text inputs / selects / number inputs ---------- */
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea {
            border-radius: 12px !important;
            border: 1px solid var(--line) !important;
        }

        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stTextArea textarea:focus {
            border-color: var(--forest-mid) !important;
            box-shadow: 0 0 0 2px rgba(47, 107, 69, 0.15) !important;
        }

        .stSelectbox [data-baseweb="select"] {
            border-radius: 12px !important;
        }

        .stMultiSelect [data-baseweb="tag"] {
            background: var(--sage-light) !important;
            color: var(--forest-dark) !important;
            border-radius: 8px !important;
        }

        /* ---------- Success / warning / info / error boxes ---------- */
        div[data-testid="stAlertContainer"] {
            border-radius: 14px;
            border-width: 1px;
            font-weight: 500;
        }

        /* ---------- Dataframes / forms container ---------- */
        div[data-testid="stForm"] {
            background: var(--card-bg);
            border-radius: 18px;
            padding: 24px;
            border: 1px solid var(--line);
            box-shadow: 0 4px 16px rgba(31, 69, 48, 0.06);
        }

        /* ---------- Accommodation cards ---------- */
        .ss-card {
            background: var(--card-bg);
            border-radius: 18px;
            padding: 20px 22px;
            margin-bottom: 16px;
            border: 1px solid var(--line);
            box-shadow: 0 4px 14px rgba(31, 69, 48, 0.07);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .ss-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(31, 69, 48, 0.12);
        }

        .ss-card h4 {
            color: var(--forest);
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-weight: 700;
            margin: 0 0 8px 0;
        }

        .ss-badge {
            display: inline-block;
            background: var(--sage-light);
            color: var(--forest-dark);
            border-radius: 999px;
            padding: 4px 13px;
            font-size: 0.78rem;
            font-weight: 600;
            margin-right: 6px;
        }

        .ss-badge.amber {
            background: rgba(224,166,61,0.18);
            color: #7a5410;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
