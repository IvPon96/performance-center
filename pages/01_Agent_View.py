#agent view 1.1 - Anti Bugs update
import streamlit as st
import plotly.express as px
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit", layout="wide")

data = load_and_process()

if data is not None:
    st.title("👤 Individual Agent Audit")
    
    agent_list = sorted(data['Full_Name'].unique())
    agent_sel = st.selectbox("Select Agent", agent_list)
    
    agent_data = data[data['Full_Name'] == agent_sel]
    date_sel = st.date_input("Audit Date", agent_data['Date_Only'].max())
    
    df_audit = agent_data[agent_data['Date_Only'] == date_sel].copy()
    
    if not df_audit.empty:
        # Aquí puedes añadir gráficas de donas o tablas específicas
        st.subheader(f"Detailed view for {agent_sel} on {date_sel}")
        st.dataframe(df_audit[['Inicio_Mx', 'Fin_Mx', 'Talk_Formatted', 'Idle_Secs']])
