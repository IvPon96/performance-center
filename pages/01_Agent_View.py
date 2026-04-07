# v1.9 - Resilient Tactical View
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
    
    # --- FILTRADO POR NIVEL DE VISTA ---
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
    else:
        quarters = sorted(df_agent['Quarter'].unique())
        q_sel = st.sidebar.selectbox("Select Quarter", quarters)
        df_final = df_agent[df_agent['Quarter'] == q_sel].copy()

    if not df_final.empty:
        st.title(f"👤 Audit: {agent_sel}")
        st.markdown(f"**Level:** {view_level} Analysis")
        st.markdown("---")

        # --- KPIs SUPERIORES ---
        talk_secs = df_final['Talk_Secs'].sum()
        idle_secs = df_final['In_Between_Idle'].sum()
        decoys = len(df_final[df_final['is_repeat'] == True])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Talk Time", format_seconds(talk_secs))
        c2.metric("Idle Between Calls", format_seconds(idle_secs))
        c3.metric("Total Calls", len(df_final))
        c4.metric("Repeat Decoys 🚨", decoys)

        st.markdown("---")

        # --- GRÁFICOS ---
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
                # Agrupamos por fecha para el gráfico de barras
                trend_data = df_final.groupby('Date_Only').size().reset_index(name='Call_Count')
                fig = px.bar(trend_data, x='Date_Only', y='Call_Count', color_discrete_sequence=['#0066cc'])
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # --- HEALTH CHECK ---
        st.subheader("🎯 Operational Health Check")
        h1, h2, h3 = st.columns(3)
        crit_count = len(df_final[df_final['Gap_Category'].isin(["Extended Idle", "Operational Gap"])])
        h1.metric("Critical Gaps (>15m)", crit_count, delta="Attention Required" if crit_count > 0 else "Normal", delta_color="inverse")
        
        doc_df = df_final[df_final['Gap_Category'] == "Standard Doc"]
        avg_doc = doc_df['In_Between_Idle'].mean() if not doc_df.empty else 0
        h2.metric("Avg Doc Time (Safe)", f"{int(avg_doc/60)}m {int(avg_doc%60)}s")
        
        has_lunch = "Detected ✅" if "Likely Lunch" in df_final['Gap_Category'].values else "Not Found ❌"
        h3.metric("Lunch Break", has_lunch)

        st.markdown("---")

        # --- LOG DETALLADO (RESILIENTE) ---
        st.subheader("📋 Detailed Operational Log")
        # Definimos las columnas que queremos mostrar
        display_cols = ['Inicio_Mx', 'Fin_Mx', 'Talk_Secs', 'num_str', 'In_Between_Idle', 'Gap_Category', 'is_repeat']
        # Solo tomamos las que realmente existan para evitar el KeyError
        actual_cols = [c for c in display_cols if c in df_final.columns]
        
        df_log = df_final[actual_cols].copy()
        df_log['Start'] = df_log['Inicio_Mx'].dt.strftime('%H:%M:%S')
        df_log['Finished'] = df_log['Fin_Mx'].dt.strftime('%H:%M:%S')
        df_log['Talk'] = df_log['Talk_Secs'].apply(format_seconds)
        df_log['Idle After'] = df_log['In_Between_Idle'].apply(format_seconds)
        
        def style_tactical(row):
            styles = [''] * len(row)
            cols_list = list(final_display.columns)
            # Colores para categorías de Gap
            if row['Category'] == "Likely Lunch": styles[cols_list.index('Category')] = 'color: #28a745; font-weight: bold;'
            elif row['Category'] == "Operational Gap": styles[cols_list.index('Category')] = 'color: #dc3545; font-weight: bold;'
            # Resaltar Repeticiones Sospechosas
            if row['is_repeat']: styles[cols_list.index('Number')] = 'background-color: #721c24; color: white;'
            return styles

        final_display = df_log[['Start', 'Finished', 'num_str', 'Talk', 'Idle After', 'Gap_Category', 'is_repeat']]
        final_display.columns = ['Start', 'Finished', 'Number', 'Talk', 'Idle After', 'Category', 'is_repeat']
        
        st.dataframe(final_display.style.apply(style_tactical, axis=1), use_container_width=True, hide_index=True)

    else:
        st.warning("No data found for this period.")
else:
    st.error("Engine failed to load data.")
