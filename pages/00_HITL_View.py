# v2.8.1 - Stable
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Operations Center", layout="wide")

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
    
    if view_level == "Daily":
        target_date = st.sidebar.date_input("Select Date", df_raw['Date_Only'].max())
        df_hitl = df_raw[df_raw['Date_Only'] == target_date].copy()
        trend_x = '15m_Interval'
    else:
        if view_level == "Weekly":
            sel = st.sidebar.selectbox("Select Week", sorted(df_raw['Week_Label'].unique(), reverse=True))
            df_hitl = df_raw[df_raw['Week_Label'] == sel].copy()
        elif view_level == "Monthly":
            sel = st.sidebar.selectbox("Select Month", sorted(df_raw['Month'].unique()))
            df_hitl = df_raw[df_raw['Month'] == sel].copy()
        else:
            df_hitl = df_raw[df_raw['Quarter'] == st.sidebar.selectbox("Select Quarter", sorted(df_raw['Quarter'].unique()))].copy()
        trend_x = 'Date_Only'

    st.title("🛰️ HITL - Operations Center")
    
    k1, k2, k3, k4 = st.columns(4)
    current_load = df_retool['Load_Count'].iloc[-1] if not df_retool.empty else 0
    k1.metric("Retool Pressure", int(current_load))
    k2.metric("Total Calls", f"{len(df_hitl):,}")
    k3.metric("Team Talk Time", format_seconds(df_hitl['Talk_Secs'].sum()))
    k4.metric("Total Decoys 🚨", f"{len(df_hitl[df_hitl['is_repeat'] == True]):,}")

    st.markdown("---")
    
    # Gráfico Dialpad Style
    st.subheader("📈 Call Volume Trend")
    trend_data = df_hitl.groupby(trend_x).size().reset_index(name='Calls')
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=trend_data[trend_x], y=trend_data['Calls'], mode='lines+markers', line=dict(color='#00ff00', width=3), fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.1)'))
    fig_trend.update_layout(plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)', height=350, xaxis=dict(gridcolor='#1f1f1f'))
    st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")
    
    # Heartbeat
    st.subheader("💓 Retool System Heartbeat")
    if not df_retool.empty:
        fig_heart = go.Figure()
        fig_heart.add_trace(go.Scatter(x=df_retool['Timestamp'], y=df_retool['Load_Count'], mode='lines+markers', line=dict(color='#00ff00', width=2), marker=dict(size=4), fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.05)'))
        fig_heart.update_layout(plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)', height=300, xaxis=dict(rangeslider=dict(visible=True), gridcolor='#1f1f1f', rangebreaks=[dict(bounds=[17, 7], pattern="hour"), dict(bounds=["sat", "mon"])]))
        st.plotly_chart(fig_heart, use_container_width=True)

    st.markdown("---")
    
    # Radar de Fricción (Allen Lund Detector)
    st.subheader("🚨 High Friction Analysis (Market Resistance)")
    # Identifica números con más de 2 intentos en el periodo
    friction = df_hitl.groupby(['num_str', 'Broker_Name']).agg({'daily_attempts': 'max', 'Talk_Secs': 'sum'}).reset_index().sort_values('daily_attempts', ascending=False)
    friction = friction[friction['daily_attempts'] > 2].head(10)
    st.dataframe(friction, column_config={"num_str": "Phone", "daily_attempts": "Intents today", "Talk_Secs": "Total Talk"}, use_container_width=True, hide_index=True)
