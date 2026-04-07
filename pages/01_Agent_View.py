# v1.8.2 - Visual Restoration & "Finished" Column
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
    
    # --- FILTRADO ---
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    elif view_level == "Weekly":
        weeks = sorted(df_agent['Week_Label'].unique(), reverse=True)
        week_sel = st.sidebar.selectbox("Select Week", weeks); df_final = df_agent[df_agent['Week_Label'] == week_sel].copy()
    elif view_level == "Monthly":
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        avail_months = [m for m in months if m in df_agent['Month'].unique()]
        month_sel = st.sidebar.selectbox("Select Month", avail_months); df_final = df_agent[df_agent['Month'] == month_sel].copy()
    else:
        quarters = sorted(df_agent['Quarter'].unique())
        q_sel = st.sidebar.selectbox("Select Quarter", quarters); df_final = df_agent[df_agent['Quarter'] == q_sel].copy()

    if not df_final.empty:
        st.title(f"👤 Audit: {agent_sel}")
        st.markdown("---")

        # --- KPIs TRADICIONALES ---
        talk_secs = df_final['Talk_Secs'].sum()
        idle_secs = df_final['In_Between_Idle'].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Talk Time", format_seconds(talk_secs))
        c2.metric("Idle Between Calls", format_seconds(idle_secs))
        c3.metric("Total Calls", len(df_final))
        c4.metric("Repeat Decoys 🚨", len(df_final[df_final['is_repeat'] == True]))

        st.markdown("---")

        # --- REINTRODUCCIÓN DE GRÁFICOS (DISTRIBUCIÓN Y TREND) ---
        col_pie, col_trend = st.columns([1, 2])
        with col_pie:
            st.subheader("Time Distribution")
            fig_pie = px.pie(names=['Talk', 'Idle'], values=[talk_secs, idle_secs], hole=0.5, color_discrete_sequence=['#0066cc', '#E5E7E9'])
            fig_pie.update_layout(margin=dict(t=20, b=20, l=0, r=0), height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_trend:
            if view_level == "Daily":
                st.subheader("Intraday Activity Pulse")
                fig = px.timeline(df_final, x_start="Inicio_Mx", x_end="Fin_Mx", y="Full_Name", color_discrete_sequence=['#0066cc'])
                fig.update_layout(yaxis_visible=False, height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.subheader("Daily Volume Trend")
                trend = df_final.groupby('Date_Only').agg({'num_str':'count'}).reset_index()
                fig = px.bar(trend, x='Date_Only', y='num_str', color_discrete_sequence=['#0066cc'])
                fig.update_layout(height=300); st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # --- HEALTH CHECK ---
        st.subheader("🎯 Operational Health Check")
        h1, h2, h3 = st.columns(3)
        crit_count = len(df_final[df_final['Gap_Category'].isin(["Extended Idle", "Operational Gap"])])
        h1.metric("Critical Gaps (>15m)", crit_count, delta="Attention Required" if crit_count > 0 else "Normal", delta_color="inverse")
        
        # FIX: Promedio de documentación
        doc_df = df_final[df_final['Gap_Category'] == "Standard Doc"]
        avg_doc = doc_df['In_Between_Idle'].mean() if not doc_df.empty else 0
        h2.metric("Avg Doc Time (Safe)", f"{int(avg_doc/60)} min {int(avg_doc%60)}s")
        
        # FIX: Lunch por periodo seleccionado
        has_lunch = "Detected ✅" if "Likely Lunch" in df_final['Gap_Category'].values else "Not Found ❌"
        h3.metric("Lunch Break", has_lunch)

        st.markdown("---")

        # --- LOG DETALLADO CON "FINISHED" ---
        st.subheader("📋 Detailed Operational Log")
        df_log = df_final[['Inicio_Mx', 'Fin_Mx', 'Talk_Secs', 'num_str', 'In_Between_Idle', 'Gap_Category', 'is_repeat']].copy()
        df_log['Start'] = df_log['Inicio_Mx'].dt.strftime('%H:%M:%S')
        df_log['Finished'] = df_log['Fin_Mx'].dt.strftime('%H:%M:%S') # LA NUEVA COLUMNA
        df_log['Talk'] = df_log['Talk_Secs'].apply(format_seconds)
        df_log['Idle After'] = df_log['In_Between_Idle'].apply(format_seconds)
        
        def style_tactical(row):
            styles = [''] * len(row)
            cols = list(df_log.columns)
            if row['Gap_Category'] == "Likely Lunch": styles[cols.index('Gap_Category')] = 'color: #28a745; font-weight: bold;'
            elif row['Gap_Category'] == "Operational Gap": styles[cols.index('Gap_Category')] = 'color: #dc3545; font-weight: bold;'
            elif row['is_repeat']: styles[cols.index('num_str')] = 'background-color: #721c24; color: white;'
            return styles

        final_display = df_log[['Start', 'Finished', 'num_str', 'Talk', 'Idle After', 'Gap_Category']]
        final_display.columns = ['Start', 'Finished', 'Number', 'Talk', 'Idle After', 'Category']
        
        st.dataframe(final_display.style.apply(style_tactical, axis=1), use_container_width=True, hide_index=True)

    else:
        st.warning("No data found.")
