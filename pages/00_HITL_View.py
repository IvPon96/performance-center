# v2.9 - Full Command Center
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

# 1. Configuración de página
st.set_page_config(page_title="HITL Operations Center", layout="wide")

# 2. CSS Estilo Radar Neón Premium
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
    
    # --- SIDEBAR: FILTROS INDEPENDIENTES ---
    st.sidebar.header("🕹️ Radar Controls")
    view_level = st.sidebar.radio("Time Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    if view_level == "Daily":
        max_date = df_raw['Date_Only'].max()
        target_date = st.sidebar.date_input("Select Date", max_date)
        df_hitl = df_raw[df_raw['Date_Only'] == target_date].copy()
        trend_x = '15m_Interval'
        trend_title = "Intraday Call Pulse (15m Intervals)"
    else:
        if view_level == "Weekly":
            weeks = sorted(df_raw['Week_Label'].unique(), reverse=True)
            sel = st.sidebar.selectbox("Select Week", weeks)
            df_hitl = df_raw[df_raw['Week_Label'] == sel].copy()
        elif view_level == "Monthly":
            months = sorted(df_raw['Month'].unique())
            sel = st.sidebar.selectbox("Select Month", months)
            df_hitl = df_raw[df_raw['Month'] == sel].copy()
        else:
            quarters = sorted(df_raw['Quarter'].unique())
            sel = st.sidebar.selectbox("Select Quarter", quarters)
            df_hitl = df_raw[df_raw['Quarter'] == sel].copy()
        
        trend_x = 'Date_Only'
        trend_title = "Historical Call Volume Trend"

    # --- TÍTULO PRINCIPAL ---
    st.title("🛰️ HITL - Operations Center")
    
    # --- KPI ROW: OPERATIONAL PULSE ---
    current_load = df_retool['Load_Count'].iloc[-1] if not df_retool.empty else 0
    prev_load = df_retool['Load_Count'].iloc[-2] if len(df_retool) > 1 else current_load
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Retool Pressure", int(current_load), delta=int(current_load - prev_load), delta_color="inverse")
    k2.metric("Total Calls (Period)", f"{len(df_hitl):,}")
    k3.metric("Team Talk Time", format_seconds(df_hitl['Talk_Secs'].sum()))
    k4.metric("Total Decoys 🚨", f"{len(df_hitl[df_hitl['is_repeat'] == True]):,}")

    st.markdown("---")

    # --- 📈 TENDENCIA DE VOLUMEN (ESTILO DIALPAD) ---
    st.subheader(trend_title)
    if not df_hitl.empty:
        trend_data = df_hitl.groupby(trend_x).size().reset_index(name='Calls')
        if trend_x == '15m_Interval':
            trend_data = trend_data.sort_values(trend_x)

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
            yaxis=dict(showgrid=True, gridcolor='#1f1f1f'),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # --- 💓 RETOOL HEARTBEAT (SHARP ANALYSIS) ---
    st.subheader("💓 Retool System Heartbeat")
    if not df_retool.empty:
        fig_heart = go.Figure()
        fig_heart.add_trace(go.Scatter(
            x=df_retool['Timestamp'], y=df_retool['Load_Count'],
            mode='lines+markers', line=dict(color='#00ff00', width=2),
            marker=dict(size=4), fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.05)',
            connectgaps=False
        ))
        fig_heart.update_layout(
            plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)', height=300,
            xaxis=dict(
                rangeslider=dict(visible=True), 
                gridcolor='#1f1f1f', 
                tickformat='%H:%M',
                rangebreaks=[
                    dict(bounds=[17, 7], pattern="hour"),
                    dict(bounds=["sat", "mon"])
                ]
            ),
            yaxis=dict(gridcolor='#1f1f1f'), margin=dict(l=20, r=20, t=10, b=10)
        )
        st.plotly_chart(fig_heart, use_container_width=True)

    st.markdown("---")

    # --- 🏢 BROKER INTELLIGENCE (TABLA Y PASTEL RESTAURADOS) ---
    c_broker, c_dist = st.columns([2, 1])
    if not df_hitl.empty:
        with c_broker:
            st.subheader("🏢 Most Contacted Brokers (Team Effort)")
            broker_rank = df_hitl['Broker_Name'].value_counts().reset_index()
            broker_rank.columns = ['Broker', 'Calls']
            with st.container(height=400):
                st.dataframe(broker_rank, 
                             column_config={
                                 "Broker": "Broker / Source",
                                 "Calls": st.column_config.ProgressColumn("Volume", format="%d", min_value=0, max_value=int(broker_rank['Calls'].max()))
                             }, use_container_width=True, hide_index=True)

        with c_dist:
            st.subheader("🌐 Broker Coverage")
            top_5 = broker_rank.head(5)
            fig_pie = px.pie(top_5, names='Broker', values='Calls', hole=0.6,
                             color_discrete_sequence=px.colors.sequential.Greens_r)
            fig_pie.update_layout(height=400, showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # --- 🚨 HIGH FRICTION ANALYSIS (EL DETECTOR DE ALLEN LUND) ---
    st.subheader("🚨 High Friction Radar (Market Resistance)")
    if not df_hitl.empty:
        friction = df_hitl.groupby(['num_str', 'Broker_Name']).agg({
            'daily_attempts': 'max', 
            'Talk_Secs': 'sum'
        }).reset_index().sort_values('daily_attempts', ascending=False)
        
        # Filtramos para mostrar solo los que tienen más de 2 intentos
        friction = friction[friction['daily_attempts'] > 2].head(15)
        
        st.write("Identificando números que están saturando la operación con reintentos múltiples:")
        st.dataframe(friction, column_config={
            "num_str": "Phone Number",
            "Broker_Name": "Broker Name",
            "daily_attempts": "Intents Today",
            "Talk_Secs": "Total Talk Time (s)"
        }, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- 🔥 HEATMAP OPERACIONAL ---
    st.subheader("🔥 Operational Intensity Heatmap")
    if not df_hitl.empty:
        heatmap_data = df_hitl.groupby(['Full_Name', '15m_Interval']).size().reset_index(name='Calls')
        heatmap_data = heatmap_data.sort_values('15m_Interval')
        fig_heat = px.density_heatmap(heatmap_data, x='15m_Interval', y='Full_Name', z='Calls',
                                      color_continuous_scale=['#0e1117', '#00ff00'], text_auto=True)
        fig_heat.update_xaxes(type='category', categoryorder='array', 
                              categoryarray=sorted(heatmap_data['15m_Interval'].unique()))
        st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.error("Error al cargar el Data Pack desde el Engine.")
