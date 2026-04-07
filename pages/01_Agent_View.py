# v1.6 - The controlio update
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

# 1. Configuración de página
st.set_page_config(page_title="Agent Audit Deep-Dive", layout="wide")

# 2. Carga de datos
data = load_and_process()

if data is not None and not data.empty:
    st.sidebar.header("Navigation Center")
    
    # Filtros de Agente y Resolución
    agent_list = sorted(data['Full_Name'].unique())
    agent_sel = st.sidebar.selectbox("Select Agent", agent_list)
    df_agent = data[data['Full_Name'] == agent_sel].copy()

    view_level = st.sidebar.radio("View Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])

    # --- LÓGICA DE FILTROS DINÁMICOS ---
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    elif view_level == "Weekly":
        weeks = sorted(df_agent['Week_Label'].unique(), reverse=True)
        week_sel = st.sidebar.selectbox("Select Week Range", weeks)
        df_final = df_agent[df_agent['Week_Label'] == week_sel].copy()
    elif view_level == "Monthly":
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        avail_months = [m for m in months if m in df_agent['Month'].unique()]
        month_sel = st.sidebar.selectbox("Select Month", avail_months)
        df_final = df_agent[df_agent['Month'] == month_sel].copy()
    else: # Quarterly
        quarters = sorted(df_agent['Quarter'].unique())
        q_sel = st.sidebar.selectbox("Select Quarter", quarters)
        df_final = df_agent[df_agent['Quarter'] == q_sel].copy()

    if not df_final.empty:
        st.title(f"👤 Audit: {agent_sel}")
        st.markdown(f"**Status:** Analysis Level {view_level}")
        st.markdown("---")

        # --- KPIs SUPERIORES ---
        total_calls = len(df_final)
        talk_secs = df_final['Talk_Secs'].sum()
        idle_secs = df_final['Idle_Secs'].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Calls", total_calls)
        c2.metric("Total Talk Time", format_seconds(talk_secs))
        c3.metric("Total Idle Time", format_seconds(idle_secs))
        c4.metric("Avg Talk Duration", f"{int(talk_secs/total_calls) if total_calls > 0 else 0}s")

        st.markdown("---")

        # --- VISUALES ---
        col_donut, col_trend = st.columns([1, 2])
        with col_donut:
            st.subheader("Time Distribution")
            fig_pie = px.pie(names=['Talk', 'Idle'], values=[talk_secs, idle_secs], hole=0.5,
                             color_discrete_sequence=['#0066cc', '#E5E7E9'])
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_trend:
            if view_level == "Daily":
                st.subheader("Intraday Activity Pulse")
                fig = px.timeline(df_final, x_start="Inicio_Mx", x_end="Fin_Mx", y="Full_Name", color_discrete_sequence=['#0066cc'])
                fig.update_layout(yaxis_visible=False, height=250, margin=dict(t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.subheader("Daily Volume Trend")
                trend_data = df_final.groupby('Date_Only').agg({'call_id':'count'}).reset_index()
                fig = px.bar(trend_data, x='Date_Only', y='call_id', color_discrete_sequence=['#0066cc'])
                fig.update_layout(height=250, margin=dict(t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # --- SECCIÓN: ATTENDANCE & READY GAP LOG (EL CORAZÓN DE LA V2.1) ---
        st.subheader("🚪 Attendance & Ready-to-Work Log")
        
        # Agrupamos por día para obtener la "verdad" de ambos sistemas
        attendance_log = df_final.groupby('Date_Only').agg(
            PC_Login=('login_dt', 'min'),
            Status=('Attendance_Status', 'first'),
            First_Call=('Inicio_Mx', 'min'),
            Ready_Gap_Val=('Ready_Gap', 'first'),
            Last_Call=('Fin_Mx', 'max'),
            SOS_Gap=('SOS_Idle', 'sum'),
            EOS_Gap=('EOS_Idle', 'sum')
        ).reset_index()

        # Formateo visual para la tabla
        attendance_log['Date'] = attendance_log['Date_Only'].astype(str)
        attendance_log['Login PC'] = attendance_log['PC_Login'].dt.strftime('%H:%M:%S').fillna("N/A")
        attendance_log['First Call'] = attendance_log['First_Call'].dt.strftime('%H:%M:%S')
        attendance_log['Last Call'] = attendance_log['Last_Call'].dt.strftime('%H:%M:%S')
        attendance_log['SOS Gap'] = attendance_log['SOS_Gap'].apply(format_seconds)
        attendance_log['EOS Gap'] = attendance_log['EOS_Gap'].apply(format_seconds)
        
        # Renombramos columnas para el usuario final
        final_table = attendance_log[['Date', 'Login PC', 'Status', 'First Call', 'Ready_Gap_Val', 'Last Call', 'SOS Gap', 'EOS Gap']]
        final_table.columns = ['Date', 'Login PC', 'Status', 'First Call', 'Ready Gap', 'Last Call', 'SOS Gap', 'EOS Gap']

        # --- Función de Estilo (Añádela antes de mostrar la tabla) ---
        def style_attendance(row):
            color = ''
            if row['Status'] == 'ON TIME':
                color = 'background-color: #d4edda; color: #155724;' # Verde suave
            elif row['Status'] == 'TARDY':
                color = 'background-color: #fff3cd; color: #856404;' # Amarillo
            elif row['Status'] == 'LATE':
                color = 'background-color: #f8d7da; color: #721c24;' # Rojo suave
            elif row['Status'] == 'NO LOG':
                color = 'background-color: #e2e3e5; color: #383d41;' # Gris
    
            return [color if v == row['Status'] else '' for v in row]

        # Mostramos la tabla
        st.subheader("🚪 Attendance & Ready-to-Work Log")

        # Aplicamos el estilo solo a la columna 'Status' para evitar colores accidentales en otras celdas
        styled_table = final_table.style.apply(style_attendance, axis=1)

        # Usamos dataframe en lugar de table para permitir el estilo
        st.dataframe(styled_table, use_container_width=True, hide_index=True)
        
        st.caption("ℹ️ **Ready Gap:** Diferencia de tiempo entre el inicio de sesión en la PC (Controlio) y la primera llamada realizada (Dialpad).")

        # --- DETALLE DE LLAMADAS ---
        with st.expander("📄 View Call-by-Call Detail"):
            st.dataframe(df_final[['Date_Only', 'Inicio_Mx', 'Fin_Mx', 'Talk_Formatted', 'external_number', 'Idle_Secs']].sort_values('Inicio_Mx'), use_container_width=True)
    else:
        st.warning("No data found for this selection.")
else:
    st.error("Engine failed to load data.")
