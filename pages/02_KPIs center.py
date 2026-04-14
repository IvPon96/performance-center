# v3.1 - Strategic Scorecard
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Strategic KPI Scorecard", layout="wide")

# Estilo Neón para coherencia con el HITL Center
st.markdown("""
    <style>
    .stMetric { background-color: #0e1117; border: 1px solid #00ff0033; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricValue"] { color: #00ff00; font-family: 'Courier New', monospace; }
    .kpi-container { background-color: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(0, 255, 0, 0.2); }
    </style>
""", unsafe_allow_html=True)

data_pack = load_and_process()

if data_pack:
    df_main = data_pack['main']
    df_goals = data_pack['kpi_goals']
    
    st.title("🏆 Strategic KPI Scorecard - Q2")
    st.write("Cálculo automatizado de bonos y cumplimiento basado en metas registradas.")

    # --- BARRA LATERAL DE FILTROS ---
    st.sidebar.header("📊 Filter Context")
    month_sel = st.sidebar.selectbox("Select Month", ["January", "February", "March", "April"])
    agent_sel = st.sidebar.selectbox("Select Agent", sorted(df_main['Full_Name'].unique()))
    
    # --- PROCESAMIENTO DE DATOS ---
    # Filtrar datos por mes y agente
    df_filtered = df_main[(df_main['Month'] == month_sel) & (df_main['Full_Name'] == agent_sel)].copy()
    goals_filtered = df_goals[df_goals['Month'] == month_sel].copy()

    if not goals_filtered.empty and not df_filtered.empty:
        st.markdown("---")
        
        # 1. CÁLCULOS DE PERFORMANCE REAL
        days_active = df_filtered['Date_Only'].nunique()
        total_calls = len(df_filtered)
        avg_calls = total_calls / days_active if days_active > 0 else 0
        
        # Inactive Time (Promedio diario excluyendo Lunch)
        idle_raw = df_filtered[df_filtered['Gap_Category'] != "🥗 Likely Lunch"]['In_Between_Idle'].sum()
        avg_idle_secs = idle_raw / days_active if days_active > 0 else 0
        
        # --- OBTENCIÓN DE METAS ---
        def get_goal_val(kpi_name):
            try:
                val = goals_filtered[goals_filtered['KPI'].str.contains(kpi_name, case=False)]['Goal'].values[0]
                return val
            except: return None

        goal_calls = float(get_goal_val('Calls'))
        goal_idle_str = get_goal_val('Inactive')
        
        # --- DASHBOARD DE MÉTRICAS ---
        col_main, col_score = st.columns([2, 1])
        
        with col_main:
            st.subheader(f"📅 Results for {agent_sel} ({month_sel})")
            
            m1, m2, m3 = st.columns(3)
            
            # KPI: CALLS PER DAY
            status_calls = avg_calls >= goal_calls
            m1.metric("Avg Calls/Day", f"{avg_calls:.1f}", 
                      delta=f"{avg_calls - goal_calls:.1f} vs Goal ({goal_calls})",
                      delta_color="normal" if status_calls else "inverse")
            
            # KPI: INACTIVE TIME
            # Convertimos meta HH:MM:SS a segundos para comparar
            if goal_idle_str:
                h, m, s = map(int, goal_idle_str.split(':'))
                goal_idle_secs = h * 3600 + m * 60 + s
                status_idle = avg_idle_secs <= goal_idle_secs
                m2.metric("Avg Inactive Time", format_seconds(avg_idle_secs), 
                          delta=f"Limit: {goal_idle_str}", 
                          delta_color="normal" if status_idle else "inverse")
            
            # KPI: DAYS ACTIVE
            m3.metric("Days Logged", days_active)

        with col_score:
            st.subheader("🎯 Final Weighting")
            # Simulación de Score Card y Attendance (Ya que son manuales)
            attendance_val = st.number_input("Input Attendance % (Manual)", value=95.0, step=0.5)
            score_card_val = st.number_input("Input Score Card % (Manual)", value=100.0, step=5.0)
            
            # Cálculo del Score Ponderado (Simplificado)
            # Nota: Esto es una base, podemos pulir la fórmula exacta después
            st.write("**Weights applied for Q2:**")
            st.code(f"Attendance: 30% | Score Card: 35% | Calls: 35%")

        st.markdown("---")
        
        # --- GRÁFICA DE CUMPLIMIENTO (GAUGE) ---
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = (avg_calls / goal_calls) * 100 if goal_calls > 0 else 0,
            title = {'text': "Volume Achievement %"},
            gauge = {
                'axis': {'range': [0, 150]},
                'bar': {'color': "#00ff00"},
                'steps': [
                    {'range': [0, 100], 'color': "#333"},
                    {'range': [100, 150], 'color': "#004400"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 100
                }
            }
        ))
        fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white", 'family': "Arial"})
        st.plotly_chart(fig_gauge, use_container_width=True)

        # --- TABLA DE REFERENCIA ---
        with st.expander("View Month Goals Strategy"):
            st.table(goals_filtered)
            
    else:
        st.warning(f"No hay metas registradas o datos de llamadas para {agent_sel} en {month_sel}.")
        st.info("Asegúrate de que el mes en Google Sheets coincida exactamente (ej. 'April') y que el agente haya realizado llamadas.")

else:
    st.error("Error al conectar con el Neural Backbone.")
