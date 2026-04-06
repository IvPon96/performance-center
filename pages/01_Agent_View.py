# Agent view v 1.0
import streamlit as st
import plotly.express as px
from data_engine import load_and_process, format_seconds # <--- IMPORTACIÓN

st.set_page_config(page_title="Individual Agent Audit", layout="wide")

# Streamlit mantiene la sesión, re-login no es necesario
data = load_and_process()

if data is not None:
    st.title("👤 Individual Agent Audit")
    
    # 1. Filtro por Agente
    all_agents = sorted(data['Full_Name'].unique())
    agent_sel = st.selectbox("Select Agent to Audit", all_agents)
    
    # 2. Filtro por Fecha
    agent_data = data[data['Full_Name'] == agent_sel]
    date_sel = st.date_input("Audit Date", agent_data['Date_Only'].max())
    
    # 3. Vista Detallada
    df_audit = agent_data[agent_data['Date_Only'] == date_sel]
    
    if not df_audit.empty:
        st.subheader(f"Performance Details for {agent_sel}")
        # Aquí podemos poner tablas específicas, métricas de SOS/EOS 
        # y un gráfico de barras solo para este agente.
        st.write(df_audit[['Inicio_Mx', 'Fin_Mx', 'Talk_Formatted', 'Idle_Secs']])
