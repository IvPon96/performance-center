# v2.3 - Broker Intel Edition
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Operations Center", layout="wide")

# CSS Radar/Neon Afilado
st.markdown("""
    <style>
    .stMetric { background-color: #0e1117; border: 1px solid #00ff0033; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricValue"] { color: #00ff00; font-family: 'Courier New', monospace; text-shadow: 0 0 5px #00ff00; }
    .stDataFrame { border: 1px solid #00ff0022; }
    </style>
""", unsafe_allow_html=True)

data_pack = load_and_process()

if data_pack:
    st.sidebar.header("🕹️ Radar Controls")
    view_level = st.sidebar.radio("Time Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    df_raw = data_pack['main']
    
    # --- LÓGICA DE FILTRADO INDEPENDIENTE ---
    if view_level == "Daily":
        target_date = st.sidebar.date_input("Select Date", df_raw['Date_Only'].max())
        df_hitl = df_raw[df_raw['Date_Only'] == target_date].copy()
        trend_x = '15m_Interval' # Eje X para Daily
        trend_title = "Intraday Call Pulse (15m Intervals)"
    else:
        # Filtros para periodos largos
        if view_level == "Weekly":
            sel = st.sidebar.selectbox("Select Week", sorted(df_raw['Week_Label'].unique(), reverse=True))
            df_hitl = df_raw[df_raw['Week_Label'] == sel].copy()
        elif view_level == "Monthly":
            sel = st.sidebar.selectbox("Select Month", sorted(df_raw['Month'].unique()))
            df_hitl = df_raw[df_raw['Month'] == sel].copy()
        else:
            sel = st.sidebar.selectbox("Select Quarter", sorted(df_raw['Quarter'].unique()))
            df_hitl = df_raw[df_raw['Quarter'] == sel].copy()
        
        trend_x = 'Date_Only' # Eje X para otros periodos
        trend_title = "Historical Call Volume Trend"

    df_retool = data_pack['retool']

    st.title("🛰️ HITL - Operations Center")
    
    # --- KPI ROW ---
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
    
    # Agrupación dinámica según el filtro
    trend_data = df_hitl.groupby(trend_x).size().reset_index(name='Calls')
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend_data[trend_x], y=trend_data['Calls'],
        mode='lines+markers',
        line=dict(color='#00ff00', width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 255, 0, 0.1)',
        marker=dict(size=6, color='#0e1117', line=dict(width=2, color='#00ff00'))
    ))
    fig_trend.update_layout(
        plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)',
        height=350, margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=True, gridcolor='#1f1f1f', title=None),
        yaxis=dict(showgrid=True, gridcolor='#1f1f1f', title="Calls Volume")
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # --- RETOOL HEARTBEAT (Picos y Valles Pronunciados) ---
    st.subheader("💓 Retool System Heartbeat (Sharp Analysis)")
    if not df_retool.empty:
        fig_heart = go.Figure()
        fig_heart.add_trace(go.Scatter(
            x=df_retool['Timestamp'], y=df_retool['Load_Count'],
            mode='lines+markers', 
            #shape='linear' por defecto hace que los picos sean picos reales
            line=dict(color='#00ff00', width=2),
            marker=dict(size=4),
            fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.05)'
        ))
        fig_heart.update_layout(
            plot_bgcolor='black', paper_bgcolor='rgba(0,0,0,0)', height=300,
            xaxis=dict(rangeslider=dict(visible=True), gridcolor='#1f1f1f', tickformat='%H:%M'),
            yaxis=dict(gridcolor='#1f1f1f'), margin=dict(l=20, r=20, t=10, b=10)
        )
        st.plotly_chart(fig_heart, use_container_width=True)

    st.markdown("---")

    # --- NUEVA SECCIÓN: BROKER INTELLIGENCE ---
    c_broker, c_dist = st.columns([2, 1])
    
    with c_broker:
        st.subheader("🏢 Most Contacted Brokers (Team Effort)")
        # Ranking de Brokers con scroll
        broker_rank = df_hitl['Broker_Name'].value_counts().reset_index()
        broker_rank.columns = ['Broker', 'Calls']
        
        # Limitamos la visualización con un contenedor de altura fija
        with st.container(height=400):
            st.dataframe(broker_rank, 
                         column_config={
                             "Broker": "Broker / Source",
                             "Calls": st.column_config.ProgressColumn("Volume", format="%d", min_value=0, max_value=int(broker_rank['Calls'].max()))
                         }, use_container_width=True, hide_index=True)

    with c_dist:
        st.subheader("🌐 Broker Coverage")
        # Top 5 vs Others para el Pie
        top_brokers = broker_rank.head(5)
        others_count = broker_rank['Calls'].iloc[5:].sum() if len(broker_rank) > 5 else 0
        
        if others_count > 0:
            pie_data = pd.concat([top_brokers, pd.DataFrame([{'Broker': 'Others', 'Calls': others_count}])])
        else:
            pie_data = top_brokers

        fig_pie = px.pie(pie_data, names='Broker', values='Calls', hole=0.6,
                         color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_pie.update_layout(height=400, showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- HEATMAP DE INTENSIDAD (OPERACIONAL) ---
    st.markdown("---")
    st.subheader("🔥 Operational Intensity Heatmap (Agent Performance)")
    heatmap_data = df_hitl.groupby(['Full_Name', '15m_Interval']).size().reset_index(name='Calls')
    fig_heat = px.density_heatmap(heatmap_data, x='15m_Interval', y='Full_Name', z='Calls',
                                  color_continuous_scale=['#0e1117', '#00ff00'], text_auto=True)
    st.plotly_chart(fig_heat, use_container_width=True)
