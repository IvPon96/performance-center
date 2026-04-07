# v1.8.1 - Final Tactical View
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit Deep-Dive", layout="wide")
data = load_and_process()

if data is not None and not data.empty:
    st.sidebar.header("Navigation Center")
    agent_sel = st.sidebar.selectbox("Select Agent", sorted(data['Full_Name'].unique()))
    df_agent = data[data['Full_Name'] == agent_sel].copy()
    
    view_level = st.sidebar.radio("Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    # --- LÓGICA DE FILTRADO COMPLETA ---
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    elif view_level == "Weekly":
        weeks = sorted(df_agent['Week_Label'].unique(), reverse=True)
        week_sel = st.sidebar.selectbox("Select Week", weeks)
        df_final = df_agent[df_agent['Week_Label'] == week_sel].copy()
    elif view_level == "Monthly":
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        avail_months = [m for m in months if m in df_agent['Month'].unique()]
        month_sel = st.sidebar.selectbox("Select Month", avail_months)
        df_final = df_agent[df_agent['Month'] == month_sel].copy()
    else: 
        quarters = sorted(df_agent['Quarter'].unique())
        q_sel = st.sidebar.selectbox("Select Quarter", quarters)
        df_final = df_agent[df_agent['Quarter'] == q_sel].copy()

    if not df_final.empty:
        st.title(f"👤 Audit: {agent_sel}")
        st.markdown(f"**Focus:** {view_level} Analysis")
        st.markdown("---")

        # --- KPI ROW 1: TRADITIONAL ---
        talk_secs = df_final['Talk_Secs'].sum()
        idle_secs = df_final['In_Between_Idle'].sum()
        # Protección para is_repeat
        decoys_count = len(df_final[df_final['is_repeat']]) if 'is_repeat' in df_final.columns else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Talk Time", format_seconds(talk_secs))
        c2.metric("Idle Between Calls", format_seconds(idle_secs))
        c3.metric("Total Calls", len(df_final))
        c4.metric("Repeat Decoys", decoys_count)

        st.markdown("---")

        # --- KPI ROW 2: HEALTH CHECK ---
        st.subheader("🎯 Operational Health Check")
        h1, h2, h3 = st.columns(3)
        
        # Gaps Críticos
        crit_cats = ["Extended Idle", "Operational Gap"]
        critical_gaps = len(df_final[df_final['Gap_Category'].isin(crit_cats)]) if 'Gap_Category' in df_final.columns else 0
        h1.metric("Critical Gaps (>15m)", critical_gaps, delta="Review" if critical_gaps > 0 else "OK", delta_color="inverse")
        
        # Doc Time
        doc_data = df_final[df_final['Gap_Category'] == "Standard Doc"] if 'Gap_Category' in df_final.columns else pd.DataFrame()
        avg_doc = doc_data['In_Between_Idle'].mean() if not doc_data.empty else 0
        h2.metric("Avg Doc Time (Safe)", f"{int(avg_doc/60)} min")
        
        # Lunch
        has_lunch = "Detected ✅" if "Likely Lunch" in df_final.get('Gap_Category', pd.Series()).values else "Not Found ❌"
        h3.metric("Lunch Break", has_lunch)

        st.markdown("---")

        # --- ACTIVITY LOG ---
        st.subheader("📋 Detailed Operational Log")
        
        df_display = df_final[['Inicio_Mx', 'Talk_Secs', 'external_number', 'In_Between_Idle', 'Gap_Category', 'is_repeat']].copy()
        df_display['Start'] = df_display['Inicio_Mx'].dt.strftime('%H:%M:%S')
        df_display['Talk'] = df_display['Talk_Secs'].apply(format_seconds)
        df_display['Idle After'] = df_display['In_Between_Idle'].apply(format_seconds)
        
        def style_tactical(row):
            styles = [''] * len(row)
            cols = list(df_display.columns)
            if row['Gap_Category'] == "Likely Lunch": styles[cols.index('Gap_Category')] = 'color: #28a745; font-weight: bold;'
            elif row['Gap_Category'] == "Operational Gap": styles[cols.index('Gap_Category')] = 'color: #dc3545; font-weight: bold;'
            elif row['Gap_Category'] == "Extended Idle": styles[cols.index('Gap_Category')] = 'color: #fd7e14; font-weight: bold;'
            if row['is_repeat']: styles[cols.index('is_repeat')] = 'background-color: #fff3cd; color: #856404; font-weight: bold;'
            return styles

        styled_log = df_display[['Start', 'external_number', 'Talk', 'Idle After', 'Gap_Category', 'is_repeat']].style.apply(style_tactical, axis=1)
        st.dataframe(styled_log, use_container_width=True, hide_index=True)

    else:
        st.warning("No data found.")
