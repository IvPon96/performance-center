import streamlit as st
from dotenv import load_dotenv
import os
load_dotenv()

st.set_page_config(page_title="BPO OPS Center", layout="wide")

st.title("📊 BPO Ops Center — Live Demo")
st.markdown("---")

st.markdown("""
            ### What is this?

            A real operational dashboard built to monitor outbound call center activity.
            It gives both a **fleet-wide view** and a **per-agent breakdown** of how agents
            distribute their time across a full workday.

            Built with real data — anonymized for this demo.            
""")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔍 What can you explore")
    st.markdown("""
                - **HITL View** — Fleet-wide timeline, call volume heatmap, and workload by interval
                - **Agent View** — Individual talk time, idle time, and daily activity feed                
                """)
    
with col2:
    st.markdown("### 🛠️ Built with")
    st.markdown("""
                - Python + Streamlit
                - Plotly Express
                - Pandas
                - Google Sheets (ETL Source)
                - Github + CodeSpaces
                - Claude as advisor
                """)
    
    st.markdown("---")
    st.markdown("Built by **Iván Ponce** — Team Leader transitioning into Analytics Engineering")
    st.markdown("[Connect on LinkedIn](https://www.linkedin.com/in/ivan-ponce-rodriguez-8640832ba) 🔗")