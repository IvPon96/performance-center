# v4.0 - Corporate Portfolio Edition (Global Operations Center)
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

# 1. Page Configuration
st.set_page_config(page_title="Global Operations Center", layout="wide")

# 2. Clean Corporate Styling
data_pack = load_and_process()

if data_pack:
    df_raw = data_pack['main']
    df_retool = data_pack['retool']
    
    # --- SIDEBAR: DASHBOARD FILTERS ---
    st.sidebar.header("📊 Dashboard Filters")
    view_level = st.sidebar.radio("Time Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    if view_level == "Daily":
        max_date = df_raw['Date_Only'].max()
        target_date = st.sidebar.date_input("Select Date", max_date)
        df_hitl = df_raw[df_raw['Date_Only'] == target_date].copy()
        trend_x = '15m_Interval'
        trend_title = "Intraday Task Execution (15m Intervals)"
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
        trend_title = "Historical Task Execution Trend"

    # --- MAIN TITLE ---
    st.title("🌐 Global Operations Center")
    st.markdown("Monitoring system workload vs. team execution efficiency.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- BLOCK 1: EXECUTIVE SUMMARY (KPIs) ---
    current_load = df_retool['Load_Count'].iloc[-1] if not df_retool.empty else 0
    prev_load = df_retool['Load_Count'].iloc[-2] if len(df_retool) > 1 else current_load
    
    total_tasks = len(df_hitl)
    redundant_tasks = len(df_hitl[df_hitl['is_repeat'] == True])
    redundancy_rate = (redundant_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Current System Workload", f"{int(current_load):,}", delta=int(current_load - prev_load), delta_color="inverse")
    k2.metric("Total Executed Tasks", f"{total_tasks:,}")
    k3.metric("Total Productive Time", format_seconds(df_hitl['Talk_Secs'].sum()))
    k4.metric("Redundancy Rate (Bottleneck)", f"{redundancy_rate:.1f}%", help="Percentage of tasks spent on already contacted/unresponsive targets.")

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # --- BLOCK 2: WORKLOAD VS EXECUTION (THE STORY) ---
    st.subheader("📈 Workload Backlog vs. Team Execution")
    st.markdown("Analyzing how the team's output correlates with the volume of incoming system tasks.")
    
    col_charts_1, col_charts_2 = st.columns(2)
    
    with col_charts_1:
        st.markdown("**System Workload Trend (Inbound Queue)**")
        if not df_retool.empty:
            fig_heart = go.Figure()
            fig_heart.add_trace(go.Scatter(
                x=df_retool['Timestamp'], y=df_retool['Load_Count'],
                mode='lines', line=dict(color='#1f77b4', width=2),
                fill='tozeroy', fillcolor='rgba(31, 119, 180, 0.1)'
            ))
            fig_heart.update_layout(
                template='plotly_white', height=300,
                xaxis=dict(
                    gridcolor='#e9ecef', tickformat='%H:%M',
                    rangebreaks=[dict(bounds=[17, 7], pattern="hour"), dict(bounds=["sat", "mon"])]
                ),
                yaxis=dict(gridcolor='#e9ecef'), margin=dict(l=0, r=0, t=10, b=10)
            )
            st.plotly_chart(fig_heart, use_container_width=True)
        else:
            st.info("System workload data currently unavailable.")

    with col_charts_2:
        st.markdown(f"**{trend_title} (Outbound Activity)**")
        if not df_hitl.empty:
            trend_data = df_hitl.groupby(trend_x).size().reset_index(name='Tasks')
            if trend_x == '15m_Interval':
                trend_data = trend_data.sort_values(trend_x)

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=trend_data[trend_x], y=trend_data['Tasks'],
                marker_color='#2ca02c'
            ))
            fig_trend.update_layout(
                template='plotly_white', height=300,
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor='#e9ecef'),
                margin=dict(l=0, r=0, t=10, b=10)
            )
            st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # --- BLOCK 3: BEHAVIORAL INTELLIGENCE ---
    st.subheader("🧠 Behavioral Intelligence & Audit")
    
    col_audit_1, col_audit_2 = st.columns([1, 1])
    
    with col_audit_1:
        st.markdown("**Operational Intensity Heatmap**")
        st.markdown("<span style='font-size:0.9em; color:gray;'>Identifies coverage gaps and team pacing.</span>", unsafe_allow_html=True)
        if not df_hitl.empty:
            heatmap_data = df_hitl.groupby(['Full_Name', '15m_Interval']).size().reset_index(name='Tasks')
            heatmap_data = heatmap_data.sort_values('15m_Interval')
            # Changed to a corporate blue color scale
            fig_heat = px.density_heatmap(heatmap_data, x='15m_Interval', y='Full_Name', z='Tasks',
                                          color_continuous_scale='Blues', text_auto=True)
            fig_heat.update_layout(template='plotly_white', height=400, margin=dict(l=0, r=0, t=10, b=10))
            fig_heat.update_xaxes(type='category', categoryorder='array', categoryarray=sorted(heatmap_data['15m_Interval'].unique()))
            st.plotly_chart(fig_heat, use_container_width=True)

    with col_audit_2:
        st.markdown("**Bottleneck Detection (Redundant Outreach)**")
        st.markdown("<span style='font-size:0.9em; color:gray;'>Targets receiving excessive attempts with minimal productive time.</span>", unsafe_allow_html=True)
        if not df_hitl.empty:
            friction = df_hitl.groupby(['num_str', 'Broker_Name']).agg({
                'daily_attempts': 'max', 
                'Talk_Secs': 'sum'
            }).reset_index().sort_values('daily_attempts', ascending=False)
            
            # Filter targets with high friction
            friction = friction[friction['daily_attempts'] > 2].head(10)
            
            st.dataframe(friction, column_config={
                "num_str": "Phone Number",
                "Broker_Name": "Target Entity",
                "daily_attempts": "Total Attempts",
                "Talk_Secs": "Total Productive Time (s)"
            }, use_container_width=True, hide_index=True)

else:
    st.error("Error loading the Data Pack from the integration engine.")