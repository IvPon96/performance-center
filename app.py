import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="Global Operations Center", layout="wide")

st.title("🌐 Global Operations Center — Live Demo")
st.markdown("---")

st.markdown("""
### What is this?
An enterprise-grade analytics engine built to monitor system workloads, optimize team execution, and detect operational bottlenecks in a BPO environment. 

Instead of just tracking raw volume, this dashboard correlates **inbound system pressure** with **outbound team execution**, highlighting redundant efforts and exposing the true productive capacity of the operation.

*Built with real operational data — fully anonymized for this public portfolio demo via a custom Python ETL pipeline.*
""")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔍 What you can explore")
    st.markdown("""
    - **Global Operations (Overview):** Fleet-wide backlog vs. execution trends, pacing heatmaps, and bottleneck (redundancy) detection.
    - **Individual Audit (Drill-down):** Behavioral tracking, productive vs. system idle time distribution, and chronological task logs.
    """)
    
with col2:
    st.markdown("### 🛠️ Tech Stack & Architecture")
    st.markdown("""
    - **Frontend:** Python + Streamlit + Plotly
    - **Data Processing:** Pandas + Custom "Neural Backbone" Join Engine
    - **Data Pipeline:** Google Sheets API + Custom ETL Anonymization Script
    - **Environment:** GitHub + Codespaces + Streamlit Cloud
    """)

st.markdown("---")
st.markdown("Built by **Iván Ponce** — Operations Leader transitioning into Analytics Engineering.")
st.markdown("[Connect on LinkedIn](https://www.linkedin.com/in/ivan-ponce-rodriguez-8640832ba) 🔗 | [View Source Code on GitHub](https://github.com/IvPon96/performance-center) 💻")