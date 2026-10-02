# modules/theme.py
# Custom visual theme for StudentStay Colombo.
# Injects CSS to restyle Streamlit's default components.

import streamlit as st


def inject_custom_css():
    st.markdown(
        """
        <style>
        /* ---------- Color palette ---------- */
        :root{
            --forest-dark:  #122118;
            --forest:       #1b3a2b;
            --forest-mid:   #2f5f45;
            --sage:         #8fbf9f;
            --amber:        #e0a63d;
            --cream:        #f3f1e8;
            --card-bg:      #ffffff;
            --text-dark:    #1c2b22;
            --text-muted:   #5c6b61;
        }

        /* ---------- Overall app background ---------- */
        .stApp {
            background: var(--cream);
        }

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {
            background: var(--forest-dark);
        }
        section[data-testid="stSidebar"] * {
            color: var(--cream) !important;
        }

        /* ---------- Buttons ---------- */
        .stButton > button {
            background: var(--forest-mid);
            color: white;
            border: none;
            border-radius: 999px;
            padding: 10px 24px;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            background: var(--amber);
            color: var(--forest-dark);
            transform: translateY(-1px);
        }
        .stButton > button[kind="primary"] {
            background: var(--amber);
            color: var(--forest-dark);
        }

        /* ---------- Metrics (the 3 stat boxes) ---------- */
        div[data-testid="stMetric"] {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 18px 20px;
            border: 1px solid #e3e0d4;
            box-shadow: 0 2px 10px rgba(27, 58, 43, 0.06);
        }
        div[data-testid="stMetricValue"] {
            color: var(--forest);
            font-weight: 700;
        }
        div[data-testid="stMetricLabel"] {
            color: var(--text-muted);
        }

        /* ---------- Tabs ---------- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background: var(--card-bg);
            padding: 6px;
            border-radius: 14px;
            border: 1px solid #e3e0d4;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 10px 16px;
            color: var(--text-muted);
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background: var(--forest) !important;
            color: white !important;
        }

        /* ---------- Expanders (Data warnings, Developer tools, Admin) ---------- */
        div[data-testid="stExpander"] {
            background: var(--card-bg);
            border-radius: 14px;
            border: 1px solid #e3e0d4;
        }

        /* ---------- Text inputs / selects ---------- */
        .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] {
            border-radius: 10px !important;
        }

        /* ---------- Accommodation cards (used inside Search & Filter / Compare) ---------- */
        .ss-card {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 18px 20px;
            margin-bottom: 14px;
            border: 1px solid #e3e0d4;
            box-shadow: 0 2px 10px rgba(27, 58, 43, 0.06);
        }
        .ss-card h4 {
            color: var(--forest);
            margin: 0 0 6px 0;
        }
        .ss-badge {
            display: inline-block;
            background: var(--sage);
            color: var(--forest-dark);
            border-radius: 999px;
            padding: 3px 12px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )