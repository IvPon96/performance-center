#v2.0 - Operations Center
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Operations Center", layout="wide")

# CSS para el look de "Centro de Control"
st.markdown("""
    <style>
    .stMetric { background-color: #0e1117; border: 1px solid #31333F; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricValue"] { color: #00ff00; font-family: 'Courier New', monospace; }
    </style>
""", unsafe_allow_html=True)

data_pack = load_and_process()

if data_pack:
    df_all = data_pack['main']
    df_retool = data_pack['retool']
    
    st.title("🛰️ HITL - Operations Center")
    st.markdown("### Real-Time Logistics Monitoring")

    # --- KPI ROW: OPERATIONAL PULSE ---
    # Obtenemos el último conteo de Retool
    current_load = df_retool['Load_Count'].iloc[-1] if not df_retool.empty else 0
    prev_load = df_retool['Load_Count'].iloc[-2] if len(df_retool) > 1 else current_load
    diff = current_load - prev_load

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Retool Pressure (Loads)", int(current_load), delta=int(diff), delta_color="inverse")
    k2.metric("Active Team Calls", len(df_all))
    k3.metric("Global Talk Time", format_seconds(df_all['Talk_Secs'].sum()))
    k4.metric("Anomalies (Repeats)", len(df_all[df_all['is_repeat'] == True]))

    st.markdown("---")

    # --- EL MARCAPASOS (Retool Heartbeat) ---
    st.subheader("💓 Retool System Heartbeat (Load Volume)")
    if not df_retool.empty:
        fig_heart = go.Figure()
        
        # Línea estilo EKG
        fig_heart.add_trace(go.Scatter(
            x=df_retool['Timestamp'], 
            y=df_retool['Load_Count'],
            mode='lines+markers',
            line=dict(color='#00ff00', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 0, 0.1)',
            name='Loads'
        ))

        fig_heart.update_layout(
            plot_bgcolor='black',
            paper_bgcolor='rgba(0,0,0,0)',
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(showgrid=True, gridcolor='#1f1f1f', tickformat='%H:%M'),
            yaxis=dict(showgrid=True, gridcolor='#1f1f1f', title="Load Count")
        )
        st.plotly_chart(fig_heart, use_container_width=True)

    st.markdown("---")

    # --- TÁCTICA DE EQUIPO ---
    col_rank, col_gaps = st.columns([2, 1])
    
    with col_rank:
        st.subheader("🏆 Efficiency Ranking (True Engagement)")
        # Calculamos ranking basado en Talk % (lo que platicamos ayer)
        ranking = df_all.groupby('Full_Name').agg({
            'Talk_Secs': 'sum',
            'num_str': 'count',
            'is_repeat': 'sum',
            'Date_Only': 'nunique'
        }).reset_index()
        
        # Asumiendo 9h de turno (32400s)
        ranking['Talk_Utilization'] = (ranking['Talk_Secs'] / (ranking['Days'] * 32400)) * 100
        ranking = ranking.sort_values('Talk_Utilization', ascending=False)
        
        st.dataframe(ranking[['Full_Name', 'Talk_Utilization', 'num_str', 'is_repeat']], 
                     column_config={
                         "Talk_Utilization": st.column_config.ProgressColumn("% Utilization", format="%.1f%%", min_value=0, max_value=40),
                         "num_str": "Total Calls",
                         "is_repeat": "Repeats"
                     }, use_container_width=True, hide_index=True)

    with col_gaps:
        st.subheader("⏱️ Team Gap Pulse")
        gap_dist = df_all['Gap_Category'].value_counts().reset_index()
        fig_gap = px.pie(gap_dist, names='Gap_Category', values='count', hole=0.6,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_gap.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_gap, use_container_width=True)

    # --- MAPA DE CALOR DE ACTIVIDAD ---
    st.markdown("---")
    st.subheader("🔥 Operational Intensity Heatmap")
    heatmap_data = df_all.groupby(['Full_Name', '15m_Interval']).size().reset_index(name='Calls')
    fig_heat = px.density_heatmap(heatmap_data, x='15m_Interval', y='Full_Name', z='Calls',
                                  color_continuous_scale='Viridis', text_auto=True)
    st.plotly_chart(fig_heat, use_container_width=True)
