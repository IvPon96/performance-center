# v 1.5 - The weekly update
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit Deep-Dive", layout="wide")

data = load_and_process()

if data is not None and not data.empty:
    st.sidebar.header("Navigation Center")
    
    agent_list = sorted(data['Full_Name'].unique())
    agent_sel = st.sidebar.selectbox("Select Agent", agent_list)
    df_agent = data[data['Full_Name'] == agent_sel].copy()

    view_level = st.sidebar.radio("View Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])

    # --- LÓGICA DE FILTROS DINÁMICOS ---
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    
    elif view_level == "Weekly":
        # Las etiquetas ahora son descriptivas: W15 (Apr 07 - Apr 13)
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
        st.markdown(f"**Resolution:** {view_level} | **Period:** {week_sel if view_level == 'Weekly' else 'Selected Range'}")
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

        # --- SECCIÓN: LOGIN/LOGOUT ACTIVITY LOG (LO NUEVO) ---
        st.subheader("🚪 Login/Logout Activity Log")
        
        # Agrupamos por día para obtener los bordes del turno
        login_summary = df_final.groupby('Date_Only').agg(
            First_Call=('Inicio_Mx', 'min'),
            Last_Call=('Fin_Mx', 'max'),
            SOS_Gap=('SOS_Idle', 'sum'),
            EOS_Gap=('EOS_Idle', 'sum')
        ).reset_index()

        # Formateamos para la tabla
        login_summary['Date'] = login_summary['Date_Only'].astype(str)
        login_summary['First Call'] = login_summary['First_Call'].dt.strftime('%H:%M:%S')
        login_summary['Last Call'] = login_summary['Last_Call'].dt.strftime('%H:%M:%S')
        login_summary['SOS Gap'] = login_summary['SOS_Gap'].apply(format_seconds)
        login_summary['EOS Gap'] = login_summary['EOS_Gap'].apply(format_seconds)

        # Mostramos la tabla con estilo
        st.table(login_summary[['Date', 'First Call', 'Last Call', 'SOS Gap', 'EOS Gap']])

        # --- DETALLE DE LLAMADAS ---
        with st.expander("📄 View Call-by-Call Detail"):
            st.dataframe(df_final[['Date_Only', 'Inicio_Mx', 'Fin_Mx', 'Talk_Formatted', 'external_number', 'Idle_Secs']].sort_values('Inicio_Mx'), use_container_width=True)
    else:
        st.warning("No data found for this selection.")
