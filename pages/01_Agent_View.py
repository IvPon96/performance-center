# v2.0 - Tactical Operations Center
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit Center", layout="wide")
data = load_and_process()

if data is not None and not data.empty:
    agent_sel = st.sidebar.selectbox("Select Agent", sorted(data['Full_Name'].unique()))
    df_agent = data[data['Full_Name'] == agent_sel].copy()
    view_level = st.sidebar.radio("Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    # Filtrado Dinámico (Daily, Weekly, etc.)
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    else:
        # Simplificado: puedes reinsertar aquí tu lógica de Week_Label/Month
        df_final = df_agent.copy()

    if not df_final.empty:
        st.title(f"👤 Auditoría: {agent_sel}")
        
        # --- KPI ROW ---
        talk_secs = df_final['Talk_Secs'].sum()
        idle_secs = df_final['In_Between_Idle'].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Talk Time", format_seconds(talk_secs))
        c2.metric("Idle Between Calls", format_seconds(idle_secs))
        c3.metric("Total Calls", len(df_final))
        c4.metric("Repeated Numbers 🚨", len(df_final[df_final['is_repeat'] == True]))

        st.markdown("---")

        # --- NUEVA FILA: FRECUENCIA DE MARCACIÓN POR HORA ---
        st.subheader("📊 Frecuencia de Marcación (Hourly Activity)")
        # Agrupamos por hora y contamos llamadas
        hourly_data = df_final.groupby('Hour').size().reset_index(name='Calls')
        fig_hour = px.bar(hourly_data, x='Hour', y='Calls', 
                          labels={'Hour': 'Hora del Día (24h)', 'Calls': 'Número de Llamadas'},
                          color_discrete_sequence=['#0066cc'])
        fig_hour.update_layout(height=300, xaxis=dict(tickmode='linear'))
        st.plotly_chart(fig_hour, use_container_width=True)

        st.markdown("---")

        # --- HEALTH CHECK ---
        st.subheader("🎯 Operational Health Check")
        h1, h2, h3 = st.columns(3)
        crit_count = len(df_final[df_final['Gap_Category'].isin(["Extended Idle", "Operational Gap"])])
        h1.metric("Critical Gaps (>15m)", crit_count, delta="Atención" if crit_count > 0 else "OK", delta_color="inverse")
        
        doc_df = df_final[df_final['Gap_Category'] == "Standard Doc"]
        avg_doc = doc_df['In_Between_Idle'].mean() if not doc_df.empty else 0
        h2.metric("Avg Doc Time", f"{int(avg_doc/60)}m {int(avg_doc%60)}s")
        h3.metric("Lunch Detection", "Detected ✅" if "Likely Lunch" in df_final['Gap_Category'].values else "Not Found ❌")

        st.markdown("---")

        # --- LOG DETALLADO PARA AUDITORÍA ---
        st.subheader("📋 Detailed Operational Log (Audit Mode)")
        
        # Preparamos el DF de visualización con Fecha
        df_log = df_final[['Date_Only', 'Inicio_Mx', 'Fin_Mx', 'num_str', 'Talk_Secs', 'In_Between_Idle', 'Gap_Category', 'is_repeat']].copy()
        df_log['Date'] = df_log['Date_Only'].astype(str)
        df_log['Start'] = df_log['Inicio_Mx'].dt.strftime('%H:%M:%S')
        df_log['Finished'] = df_log['Fin_Mx'].dt.strftime('%H:%M:%S')
        df_log['Talk'] = df_log['Talk_Secs'].apply(format_seconds)
        df_log['Idle After'] = df_log['In_Between_Idle'].apply(format_seconds)
        
        # Seleccionamos y renombramos para el usuario
        final_table = df_log[['Date', 'Start', 'Finished', 'num_str', 'Talk', 'Idle After', 'Gap_Category', 'is_repeat']]
        final_table.columns = ['Date', 'Start', 'Finished', 'Number', 'Talk', 'Idle After', 'Category', 'Repeated']

        def style_audit(row):
            styles = [''] * len(row)
            # Resaltar repeticiones en Rojo/Naranja para auditoría
            if row['Repeated']:
                styles[list(final_table.columns).index('Number')] = 'background-color: #721c24; color: white; font-weight: bold;'
            # Colores para categorías
            cat_idx = list(final_table.columns).index('Category')
            if row['Category'] == "Likely Lunch": styles[cat_idx] = 'color: #28a745;'
            elif row['Category'] == "Operational Gap": styles[cat_idx] = 'color: #dc3545; font-weight: bold;'
            return styles

        st.dataframe(final_table.style.apply(style_audit, axis=1), use_container_width=True, hide_index=True)

    else:
        st.warning("No data found.")
