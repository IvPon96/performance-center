#v2.2 - Full Control Edition
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Operations Center", layout="wide")

# CSS Radar/Neon Premium
st.markdown("""
    <style>
    .stMetric { background-color: #0e1117; border: 1px solid #00ff0033; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricValue"] { color: #00ff00; font-family: 'Courier New', monospace; text-shadow: 0 0 5px #00ff00; }
    </style>
""", unsafe_allow_html=True)

data_pack = load_and_process()

if data_pack:
    # --- FILTROS INDEPENDIENTES ---
    st.sidebar.header("🕹️ Radar Controls")
    view_level = st.sidebar.radio("Time Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    df_raw = data_pack['main']
    
    # Lógica de filtrado específica para HITL View
    if view_level == "Daily":
        target_date = st.sidebar.date_input("Select Date", df_raw['Date_Only'].max())
        df_hitl = df_raw[df_raw['Date_Only'] == target_date].copy()
    elif view_level == "Weekly":
        week_sel = st.sidebar.selectbox("Select Week", sorted(df_raw['Week_Label'].unique(), reverse=True))
        df_hitl = df_raw[df_raw['Week_Label'] == week_sel].copy()
    elif view_level == "Monthly":
        month_sel = st.sidebar.selectbox("Select Month", sorted(df_raw['Month'].unique()))
        df_hitl = df_raw[df_raw['Month'] == month_sel].copy()
    else:
        df_hitl = df_raw[df_raw['Quarter'] == st.sidebar.selectbox("Select Quarter", sorted(df_raw['Quarter'].unique()))].copy()

    df_retool = data_pack['retool']

    st.title("🛰️ HITL - Operations Center")
    
    # --- KPI ROW ---
    current_load = df_retool['Load_Count'].iloc[-1] if not df_retool.empty else 0
    prev_load = df_retool['Load_Count'].iloc[-2] if len(df_retool) > 1 else current_load
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Retool Pressure", int(current_load), delta=int(current_load - prev_load), delta_color="inverse")
    k2.metric("Period Total Calls", f"{len(df_hitl):,}")
    k3.metric("Total Talk Time", format_seconds(df_hitl['Talk_Secs'].sum()))
    k4.metric("Total Decoys 🚨", f"{len(df_hitl[df_hitl['is_repeat'] == True]):,}")

    st.markdown("---")

    # --- REPLICANDO DIALPAD: CALL VOLUME OVER TIME ---
    st.subheader("📈 Call Volume Trend (Dialpad Style)")
    
    # Agrupamos por fecha para ver la tendencia
    trend_data = df_hitl.groupby('Date_Only').size().reset_index(name='Calls')
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend_data['Date_Only'], 
        y=trend_data['Calls'],
        mode='lines+markers',
        line=dict(color='#00ff00', width=3),
        fill='tozeroy', # Shaded area como el de Dialpad
        fillcolor='rgba(0, 255, 0, 0.1)',
        marker=dict(size=8, color='#0e1117', line=dict(width=2, color='#00ff00'))
    ))
    
    fig_trend.update_layout(
        plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)',
        height=350, margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=True, gridcolor='#1f1f1f', title="Timeline"),
        yaxis=dict(showgrid=True, gridcolor='#1f1f1f', title="Volume")
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # --- EL MARCAPASOS (Heartbeat de Retool) ---
    st.subheader("💓 Retool System Heartbeat")
    if not df_retool.empty:
        fig_heart = go.Figure()
        fig_heart.add_trace(go.Scatter(
            x=df_retool['Timestamp'], y=df_retool['Load_Count'],
            mode='lines', line=dict(color='#00ff00', width=2, shape='spline'),
            fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.05)'
        ))
        fig_heart.update_layout(
            plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)', height=300,
            xaxis=dict(rangeslider=dict(visible=True), gridcolor='#1f1f1f'),
            yaxis=dict(gridcolor='#1f1f1f'), margin=dict(l=20, r=20, t=10, b=10)
        )
        st.plotly_chart(fig_heart, use_container_width=True)

    st.markdown("---")

    # --- RANKING & GAPS ---
    c_rank, c_gaps = st.columns([2, 1])
    
    with c_rank:
        st.subheader("🏆 Efficiency Ranking")
        ranking = df_hitl.groupby('Full_Name').agg({
            'Talk_Secs': 'sum', 'num_str': 'count', 'is_repeat': 'sum', 'Date_Only': 'nunique'
        }).rename(columns={'Date_Only': 'Days'}).reset_index()
        
        ranking['Utilization'] = (ranking['Talk_Secs'] / (ranking['Days'] * 32400)) * 100
        ranking = ranking.sort_values('Utilization', ascending=False)
        
        st.dataframe(ranking[['Full_Name', 'Utilization', 'num_str', 'is_repeat']], 
                     column_config={
                         "Full_Name": "Agent",
                         "Utilization": st.column_config.ProgressColumn("% Engagement", format="%.1f%%", min_value=0, max_value=25),
                         "num_str": "Calls", "is_repeat": "Decoys"
                     }, use_container_width=True, hide_index=True)

    with c_gaps:
        st.subheader("⏱️ Team Gap Pulse")
        gap_dist = df_hitl['Gap_Category'].value_counts().reset_index()
        fig_gap = px.pie(gap_dist, names='Gap_Category', values='count', hole=0.6,
                         color_discrete_sequence=['#00ff00', '#00cc00', '#009900', '#006600', '#8b0000'])
        fig_gap.update_layout(height=400, showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_gap, use_container_width=True)

    # --- HEATMAP ---
    st.markdown("---")
    st.subheader("🔥 Operational Intensity Heatmap (15m Intervals)")
    heatmap_data = df_hitl.groupby(['Full_Name', '15m_Interval']).size().reset_index(name='Calls')
    fig_heat = px.density_heatmap(heatmap_data, x='15m_Interval', y='Full_Name', z='Calls',
                                  color_continuous_scale=['#0e1117', '#00ff00'], text_auto=True)
    st.plotly_chart(fig_heat, use_container_width=True)
