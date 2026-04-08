# v2.1 - Radar Edition con Scroll
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Operations Center", layout="wide")

# CSS Estilo Radar/Médico Premium
st.markdown("""
    <style>
    .stMetric { background-color: #0e1117; border: 1px solid #00ff0033; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricValue"] { color: #00ff00; font-family: 'Courier New', monospace; text-shadow: 0 0 5px #00ff00; }
    .stDataFrame { border: 1px solid #00ff0022; }
    </style>
""", unsafe_allow_html=True)

data_pack = load_and_process()

if data_pack:
    df_all = data_pack['main']
    df_retool = data_pack['retool']
    
    st.title("🛰️ HITL - Operations Center")
    st.markdown("### Real-Time Logistics Monitoring")

    # --- KPI ROW: OPERATIONAL PULSE ---
    current_load = df_retool['Load_Count'].iloc[-1] if not df_retool.empty else 0
    prev_load = df_retool['Load_Count'].iloc[-2] if len(df_retool) > 1 else current_load
    diff = current_load - prev_load

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Retool Pressure (Loads)", int(current_load), delta=int(diff), delta_color="inverse")
    k2.metric("Active Team Calls", f"{len(df_all):,}")
    k3.metric("Global Talk Time", format_seconds(df_all['Talk_Secs'].sum()))
    k4.metric("Anomalies (Repeats)", f"{len(df_all[df_all['is_repeat'] == True]):,}")

    st.markdown("---")

    # --- EL MARCAPASOS (Con Scroll Horizontal) ---
    st.subheader("💓 Retool System Heartbeat (Historical Flow)")
    if not df_retool.empty:
        fig_heart = go.Figure()
        
        fig_heart.add_trace(go.Scatter(
            x=df_retool['Timestamp'], 
            y=df_retool['Load_Count'],
            mode='lines+markers',
            line=dict(color='#00ff00', width=2, shape='spline'), # Línea suavizada
            fill='tozeroy',
            fillcolor='rgba(0, 255, 0, 0.05)',
            name='Loads',
            hovertemplate="<b>Hora:</b> %{x}<br><b>Loads:</b> %{y}<extra></extra>"
        ))

        fig_heart.update_layout(
            plot_bgcolor='black',
            paper_bgcolor='rgba(0,0,0,0)',
            height=400,
            xaxis=dict(
                showgrid=True, 
                gridcolor='#1f1f1f', 
                tickformat='%b %d, %H:%M',
                rangeslider=dict(visible=True), # ESTO ACTIVA EL SCROLL HORIZONTAL
                type='date'
            ),
            yaxis=dict(showgrid=True, gridcolor='#1f1f1f', title="Load Count"),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_heart, use_container_width=True)

    st.markdown("---")

    # --- TÁCTICA DE EQUIPO (Ranking Corregido) ---
    col_rank, col_gaps = st.columns([2, 1])
    
    with col_rank:
        st.subheader("🏆 Efficiency Ranking (True Engagement)")
        
        # FIX: Agregación con renombrado explícito para evitar KeyError
        ranking = df_all.groupby('Full_Name').agg({
            'Talk_Secs': 'sum',
            'num_str': 'count',
            'is_repeat': 'sum',
            'Date_Only': 'nunique' 
        }).rename(columns={'Date_Only': 'Days'}).reset_index() # Renombramos aquí
        
        # Cálculo de utilización (Basado en 9h = 32400s)
        ranking['Utilization'] = (ranking['Talk_Secs'] / (ranking['Days'] * 32400)) * 100
        ranking = ranking.sort_values('Utilization', ascending=False)
        
        st.dataframe(ranking[['Full_Name', 'Utilization', 'num_str', 'is_repeat']], 
                     column_config={
                         "Full_Name": "Agent",
                         "Utilization": st.column_config.ProgressColumn(
                             "% Engagement", 
                             format="%.1f%%", 
                             min_value=0, 
                             max_value=30 # 30% es un talk time saludable
                         ),
                         "num_str": "Total Calls",
                         "is_repeat": "Decoys"
                     }, use_container_width=True, hide_index=True)

    with col_gaps:
        st.subheader("⏱️ Team Gap Pulse")
        gap_dist = df_all['Gap_Category'].value_counts().reset_index()
        fig_gap = px.pie(gap_dist, names='Gap_Category', values='count', hole=0.6,
                         color_discrete_sequence=['#00ff00', '#00cc00', '#009900', '#006600', '#8b0000'])
        fig_gap.update_layout(height=400, showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_gap, use_container_width=True)

    # --- HEATMAP DE INTENSIDAD ---
    st.markdown("---")
    st.subheader("🔥 Operational Intensity Heatmap")
    heatmap_data = df_all.groupby(['Full_Name', '15m_Interval']).size().reset_index(name='Calls')
    fig_heat = px.density_heatmap(heatmap_data, x='15m_Interval', y='Full_Name', z='Calls',
                                  color_continuous_scale=['#0e1117', '#00ff00'], text_auto=True)
    fig_heat.update_layout(xaxis_title="Time Interval (15m)", yaxis_title=None)
    st.plotly_chart(fig_heat, use_container_width=True)
