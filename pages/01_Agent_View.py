# v2.2 - Strategic Navigation & Audit PRO
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit Center", layout="wide")
data = load_and_process()

if data is not None and not data.empty:
    st.sidebar.header("Navigation Center")
    agent_sel = st.sidebar.selectbox("Select Agent", sorted(data['Full_Name'].unique()))
    df_agent = data[data['Full_Name'] == agent_sel].copy()
    
    # --- RESTAURACIÓN DE SELECTORES ---
    view_level = st.sidebar.radio("Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    elif view_level == "Weekly":
        weeks = sorted(df_agent['Week_Label'].unique(), reverse=True)
        week_sel = st.sidebar.selectbox("Select Week", weeks)
        df_final = df_agent[df_agent['Week_Label'] == week_sel].copy()
    elif view_level == "Monthly":
        months = sorted(df_agent['Month'].unique())
        month_sel = st.sidebar.selectbox("Select Month", months)
        df_final = df_agent[df_agent['Month'] == month_sel].copy()
    else: # Quarterly
        quarters = sorted(df_agent['Quarter'].unique())
        q_sel = st.sidebar.selectbox("Select Quarter", quarters)
        df_final = df_agent[df_agent['Quarter'] == q_sel].copy()

    if not df_final.empty:
        st.title(f"👤 Auditoría: {agent_sel}")
        st.markdown(f"**Análisis:** {view_level}")
        
        # --- KPIs ---
        talk_secs = df_final['Talk_Secs'].sum()
        idle_secs = df_final['In_Between_Idle'].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Talk Time", format_seconds(talk_secs))
        c2.metric("Idle Between Calls", format_seconds(idle_secs))
        c3.metric("Total Calls", len(df_final))
        c4.metric("Repeated Numbers 🚨", len(df_final[df_final['is_repeat'] == True]))

        st.markdown("---")

        # --- FILA 1 DE GRÁFICOS ---
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
                trend_data = df_final.groupby('Date_Only').size().reset_index(name='Call_Count')
                fig = px.bar(trend_data, x='Date_Only', y='Call_Count', color_discrete_sequence=['#0066cc'])
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

        # --- FILA 2: FRECUENCIA (Solo para Daily) ---
        if view_level == "Daily":
            st.subheader("📊 Frecuencia de Marcación (15-Minute Intervals)")
            freq_15m = df_final.groupby('15m_Interval').size().reset_index(name='Calls')
            fig_15 = px.bar(freq_15m, x='15m_Interval', y='Calls', 
                            labels={'15m_Interval': 'Intervalo (15m)', 'Calls': 'Llamadas'},
                            color_discrete_sequence=['#00cc96'])
            fig_15.update_layout(height=300)
            st.plotly_chart(fig_15, use_container_width=True)

        st.markdown("---")

        # --- HEALTH CHECK ---
        st.subheader("🎯 Operational Health Check")
        h1, h2, h3 = st.columns(3)
        crit_count = len(df_final[df_final['Gap_Category'].isin(["Extended Idle", "Operational Gap"])])
        h1.metric("Critical Gaps (>15m)", crit_count, delta="Atención" if crit_count > 0 else "OK", delta_color="inverse")
        
        doc_df = df_final[df_final['Gap_Category'] == "Standard Doc"]
        avg_doc = doc_df['In_Between_Idle'].mean() if not doc_df.empty else 0
        h2.metric("Avg Doc Time", f"{int(avg_doc/60)}m {int(avg_doc%60)}s")
        h3.metric("Lunch Detection", "Detected ✅" if "🥗 Likely Lunch" in df_final['Gap_Category'].values else "Not Found ❌")

        st.markdown("---")

        # --- LOG DETALLADO DE AUDITORÍA ---
        st.subheader("📋 Detailed Operational Log (Audit Mode)")
        
        df_log = df_final[['Date_Only', 'Inicio_Mx', 'Fin_Mx', 'num_str', 'Talk_Secs', 'In_Between_Idle', 'Gap_Category', 'is_repeat']].copy()
        df_log['Date'] = df_log['Date_Only'].astype(str)
        df_log['Start'] = df_log['Inicio_Mx'].dt.strftime('%H:%M:%S')
        df_log['Finished'] = df_log['Fin_Mx'].dt.strftime('%H:%M:%S')
        df_log['Talk'] = df_log['Talk_Secs'].apply(format_seconds)
        df_log['Idle After'] = df_log['In_Between_Idle'].apply(format_seconds)
        
        final_table = df_log[['Date', 'Start', 'Finished', 'num_str', 'Talk', 'Idle After', 'Gap_Category', 'is_repeat']]
        final_table.columns = ['Date', 'Start', 'Finished', 'Number', 'Talk', 'Idle After', 'Category', 'Repeated']

        def style_audit_v2(row):
            styles = [''] * len(row)
            cols = list(final_table.columns)
            
            # Número repetido en Rojo Oscuro
            if row['Repeated']:
                styles[cols.index('Number')] = 'color: #8b0000; font-weight: bold;'
            
            # Colores de Categoría
            cat_idx = cols.index('Category')
            cat = row['Category']
            if "Standard Doc" in cat: styles[cat_idx] = 'color: #28a745;'
            elif "Micro-Gap" in cat: styles[cat_idx] = 'color: #ffc107;'
            elif "Extended Idle" in cat: styles[cat_idx] = 'color: #fd7e14;'
            elif "Operational Gap" in cat: styles[cat_idx] = 'color: #dc3545; font-weight: bold;'
            elif "🥗 Likely Lunch" in cat: styles[cat_idx] = 'color: #6f42c1; font-weight: bold;'
            
            return styles

        st.dataframe(final_table.style.apply(style_audit_v2, axis=1), use_container_width=True, hide_index=True)

    else:
        st.warning("No data found for this period.")
else:
    st.error("Engine failed to load data.")
