#v2.4 - Radar Stealth Edition
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Operations Center", layout="wide")

# Estética Radar Neón
st.markdown("""
    <style>
    .stMetric { background-color: #0e1117; border: 1px solid #00ff0033; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricValue"] { color: #00ff00; font-family: 'Courier New', monospace; text-shadow: 0 0 5px #00ff00; }
    </style>
""", unsafe_allow_html=True)

data_pack = load_and_process()

if data_pack:
    df_hitl = data_pack['main']
    df_retool = data_pack['retool']
    
    st.sidebar.header("🕹️ Radar Controls")
    view_level = st.sidebar.radio("Time Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    # --- FILTRADO (Igual al anterior) ---
    if view_level == "Daily":
        target_date = st.sidebar.date_input("Select Date", df_hitl['Date_Only'].max())
        df_view = df_hitl[df_hitl['Date_Only'] == target_date].copy()
    else:
        # (Aquí va tu lógica de filtrado para Weekly/Monthly/Quarterly)
        df_view = df_hitl.copy() # Simplificado para el ejemplo

    st.title("🛰️ HITL - Operations Center")
    
    # KPI Row (Igual al anterior)
    k1, k2, k3, k4 = st.columns(4)
    # ... (Tus métricas actuales)

    st.markdown("---")

    # --- EL MARCAPASOS CON SONAR (Retool + Call volume) ---
    st.subheader("💓 Retool System Heartbeat & Call Pulse")
    
    if not df_retool.empty:
        # 1. Preparar datos del "Sonar" (Llamadas en intervalos)
        # Extraemos HH:MM del timestamp de Retool para sincronizar
        df_retool['time_key'] = df_retool['Timestamp'].dt.strftime('%H:%M')
        
        # Agrupamos llamadas por intervalo para el overlay
        calls_per_int = df_view.groupby('15m_Interval').size().reset_index(name='Call_Count')
        
        # Unimos los datos para que vivan en el mismo eje X
        radar_sync = pd.merge(df_retool, calls_per_int, left_on='time_key', right_on='15m_Interval', how='left').fillna(0)

        # Crear gráfico con doble eje Y
        fig_radar = make_subplots(specs=[[{"secondary_y": True}]])

        # Trazo 1: Retool Loads (Protagonista)
        fig_radar.add_trace(
            go.Scatter(x=radar_sync['Timestamp'], y=radar_sync['Load_Count'],
                       name="Retool Loads", line=dict(color='#00ff00', width=3),
                       fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.05)'),
            secondary_y=False
        )

        # Trazo 2: Sonar Pulse (Llamadas - El "Submarino")
        fig_radar.add_trace(
            go.Scatter(x=radar_sync['Timestamp'], y=radar_sync['Call_Count'],
                       name="Team Calls (Sonar)", mode='markers+lines',
                       marker=dict(size=8, color='#00ff00', opacity=0.3), # Tenue como sonar
                       line=dict(color='#00ff00', width=1, dash='dot', shape='spline'),
                       opacity=0.3),
            secondary_y=True
        )

        fig_radar.update_layout(
            plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)', height=400,
            xaxis=dict(gridcolor='#1f1f1f', rangeslider=dict(visible=True)),
            yaxis=dict(title="Retool Loads", gridcolor='#1f1f1f'),
            yaxis2=dict(title="Calls Pulse", showgrid=False),
            showlegend=False, margin=dict(l=20, r=20, t=10, b=10)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("---")

    # --- HEATMAP CORREGIDO (Orden Cronológico) ---
    st.subheader("🔥 Operational Intensity Heatmap")
    
    # Agrupar y asegurar orden
    heatmap_data = df_view.groupby(['Full_Name', '15m_Interval']).size().reset_index(name='Calls')
    # ORDENAR: Importante para evitar el error de la imagen
    heatmap_data = heatmap_data.sort_values('15m_Interval')

    fig_heat = px.density_heatmap(
        heatmap_data, x='15m_Interval', y='Full_Name', z='Calls',
        color_continuous_scale=['#0e1117', '#00ff00'], 
        text_auto=True
    )
    
    # Forzamos al eje X a ser categórico para mantener el orden de los intervalos
    fig_heat.update_xaxes(type='category', categoryorder='array', 
                          categoryarray=sorted(heatmap_data['15m_Interval'].unique()))
    
    fig_heat.update_layout(height=450, xaxis_title="Timeline (15m Intervals)")
    st.plotly_chart(fig_heat, use_container_width=True)

    # ... (Resto de tu código de Brokers Ranking igual)
