# v2.5 - Stable Radar Edition
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Operations Center", layout="wide")

# Estética Radar Neón Premium
st.markdown("""
    <style>
    .stMetric { background-color: #0e1117; border: 1px solid #00ff0033; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricValue"] { color: #00ff00; font-family: 'Courier New', monospace; text-shadow: 0 0 5px #00ff00; }
    .stDataFrame { border: 1px solid #00ff0022; }
    </style>
""", unsafe_allow_html=True)

data_pack = load_and_process()

if data_pack:
    df_raw = data_pack['main']
    df_retool = data_pack['retool']
    
    st.sidebar.header("🕹️ Radar Controls")
    view_level = st.sidebar.radio("Time Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    # --- LÓGICA DE FILTRADO INDEPENDIENTE ---
    if view_level == "Daily":
        target_date = st.sidebar.date_input("Select Date", df_raw['Date_Only'].max())
        df_hitl = df_raw[df_raw['Date_Only'] == target_date].copy()
        trend_x = '15m_Interval'
        trend_title = "Intraday Call Pulse (15m Intervals)"
    else:
        if view_level == "Weekly":
            sel = st.sidebar.selectbox("Select Week", sorted(df_raw['Week_Label'].unique(), reverse=True))
            df_hitl = df_raw[df_raw['Week_Label'] == sel].copy()
        elif view_level == "Monthly":
            sel = st.sidebar.selectbox("Select Month", sorted(df_raw['Month'].unique()))
            df_hitl = df_raw[df_raw['Month'] == sel].copy()
        else:
            sel = st.sidebar.selectbox("Select Quarter", sorted(df_raw['Quarter'].unique()))
            df_hitl = df_raw[df_raw['Quarter'] == sel].copy()
        
        trend_x = 'Date_Only'
        trend_title = "Historical Call Volume Trend"

    st.title("🛰️ HITL - Operations Center")
    
    # --- KPI ROW: OPERATIONAL PULSE ---
    current_load = df_retool['Load_Count'].iloc[-1] if not df_retool.empty else 0
    prev_load = df_retool['Load_Count'].iloc[-2] if len(df_retool) > 1 else current_load
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Retool Pressure", int(current_load), delta=int(current_load - prev_load), delta_color="inverse")
    k2.metric("Total Calls (Period)", f"{len(df_hitl):,}")
    k3.metric("Team Talk Time", format_seconds(df_hitl['Talk_Secs'].sum()))
    k4.metric("Anomalies (Decoys)", f"{len(df_hitl[df_hitl['is_repeat'] == True]):,}")

    st.markdown("---")

    # --- TENDENCIA DINÁMICA (DIALPAD STYLE) ---
    st.subheader(f"📈 {trend_title}")
    trend_data = df_hitl.groupby(trend_x).size().reset_index(name='Calls')
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend_data[trend_x], y=trend_data['Calls'],
        mode='lines+markers', line=dict(color='#00ff00', width=3),
        fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.1)',
        marker=dict(size=6, color='#0e1117', line=dict(width=2, color='#00ff00'))
    ))
    fig_trend.update_layout(
        plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)', height=350,
        xaxis=dict(showgrid=True, gridcolor='#1f1f1f'),
        yaxis=dict(showgrid=True, gridcolor='#1f1f1f')
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # --- RETOOL HEARTBEAT (Sharp & Clean) ---
    st.subheader("💓 Retool System Heartbeat (Sharp Analysis)")
    if not df_retool.empty:
        fig_heart = go.Figure()
        fig_heart.add_trace(go.Scatter(
            x=df_retool['Timestamp'], y=df_retool['Load_Count'],
            mode='lines+markers', line=dict(color='#00ff00', width=2),
            marker=dict(size=4), fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.05)'
        ))
        fig_heart.update_layout(
            plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)', height=300,
            xaxis=dict(rangeslider=dict(visible=True), gridcolor='#1f1f1f', tickformat='%H:%M'),
            yaxis=dict(gridcolor='#1f1f1f'), margin=dict(l=20, r=20, t=10, b=10)
        )
        st.plotly_chart(fig_heart, use_container_width=True)

    st.markdown("---")

    # --- BROKER INTELLIGENCE ---
    c_broker, c_dist = st.columns([2, 1])
    with c_broker:
        st.subheader("🏢 Most Contacted Brokers")
        broker_rank = df_hitl['Broker_Name'].value_counts().reset_index()
        broker_rank.columns = ['Broker', 'Calls']
        with st.container(height=400):
            st.dataframe(broker_rank, 
                         column_config={
                             "Broker": "Broker Name",
                             "Calls": st.column_config.ProgressColumn("Volume
