# v1.8 - Tactical Dashboard Update
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit Deep-Dive", layout="wide")
data = load_and_process()

if data is not None and not data.empty:
    # --- SIDEBAR FILTERS ---
    agent_sel = st.sidebar.selectbox("Select Agent", sorted(data['Full_Name'].unique()))
    df_agent = data[data['Full_Name'] == agent_sel].copy()
    view_level = st.sidebar.radio("Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    # Filtrado (Simplificado para el ejemplo)
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    else:
        df_final = df_agent.copy() # Aquí iría tu lógica de semanas/meses

    if not df_final.empty:
        st.title(f"👤 Audit: {agent_sel}")
        
        # --- KPI ROW 1: TRADITIONAL METRICS ---
        talk_secs = df_final['Talk_Secs'].sum()
        idle_secs = df_final['In_Between_Idle'].sum() # Solo in-between para adherencia real
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Talk Time", format_seconds(talk_secs))
        c2.metric("Idle Between Calls", format_seconds(idle_secs))
        c3.metric("Total Calls", len(df_final))
        c4.metric("Repeat Decoys", len(df_final[df_final['is_repeat']]))

        st.markdown("---")

        # --- KPI ROW 2: OPERATIONAL HEALTH CHECK (EL DIAGNÓSTICO) ---
        st.subheader("🎯 Operational Health Check")
        h1, h2, h3 = st.columns(3)
        
        # 1. Gaps Críticos
        critical_gaps = len(df_final[df_final['Gap_Category'].isin(["Extended Idle", "Operational Gap"])])
        h1.metric("Critical Gaps (>15m)", critical_gaps, delta="Review Required" if critical_gaps > 0 else "Clean", delta_color="inverse")
        
        # 2. Documentación Promedio
        avg_doc = df_final[df_final['Gap_Category'] == "Standard Doc"]['In_Between_Idle'].mean()
        h2.metric("Avg Doc Time (Safe)", f"{int(avg_doc/60)} min" if not pd.isna(avg_doc) else "0 min")
        
        # 3. Lunch Detection
        has_lunch = "Detected ✅" if "Likely Lunch" in df_final['Gap_Category'].values else "Not Found ❌"
        h3.metric("Lunch Break", has_lunch)

        st.markdown("---")

        # --- TABLA DE AUDITORÍA DETALLADA ---
        st.subheader("📋 Detailed Operational Log")
        
        # Preparamos la tabla para que sea legible
        df_display = df_final[['Inicio_Mx', 'Talk_Secs', 'external_number', 'In_Between_Idle', 'Gap_Category', 'is_repeat']].copy()
        df_display['Start'] = df_display['Inicio_Mx'].dt.strftime('%H:%M:%S')
        df_display['Talk'] = df_display['Talk_Secs'].apply(format_seconds)
        df_display['Idle After'] = df_display['In_Between_Idle'].apply(format_seconds)
        
        # Función de estilo táctico
        def style_tactical(row):
            styles = [''] * len(row)
            cat_idx = list(df_display.columns).index('Gap_Category')
            rep_idx = list(df_display.columns).index('is_repeat')
            
            # Colores para Gaps
            if row['Gap_Category'] == "Likely Lunch": styles[cat_idx] = 'color: #28a745; font-weight: bold;'
            elif row['Gap_Category'] == "Operational Gap": styles[cat_idx] = 'color: #dc3545; font-weight: bold;'
            elif row['Gap_Category'] == "Extended Idle": styles[cat_idx] = 'color: #fd7e14; font-weight: bold;'
            
            # Resaltar Repeticiones Sospechosas
            if row['is_repeat']: styles[rep_idx] = 'background-color: #fff3cd; color: #856404; font-weight: bold;'
            
            return styles

        styled_log = df_display[['Start', 'external_number', 'Talk', 'Idle After', 'Gap_Category', 'is_repeat']].style.apply(style_tactical, axis=1)
        st.dataframe(styled_log, use_container_width=True, hide_index=True)

    else:
        st.warning("No data found.")
