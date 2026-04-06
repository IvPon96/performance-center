# v 1.4 - The "time" update

import streamlit as st
import plotly.express as px
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit Deep-Dive", layout="wide")

data = load_and_process()

if data is not None and not data.empty:
    st.sidebar.header("Navigation Center")
    
    # 1. Filtro de Agente
    agent_list = sorted(data['Full_Name'].unique())
    agent_sel = st.sidebar.selectbox("Select Agent", agent_list)
    df_agent = data[data['Full_Name'] == agent_sel].copy()

    # 2. Selector de Nivel de Vista (LA MAGIA)
    view_level = st.sidebar.radio("View Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])

    # 3. Filtros Dinámicos según la resolución
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    
    elif view_level == "Weekly":
        weeks = sorted(df_agent['Week_Label'].unique(), reverse=True)
        week_sel = st.sidebar.selectbox("Select ISO Week", weeks)
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

    # --- RENDERIZADO DEL DASHBOARD ---
    if not df_final.empty:
        st.title(f"👤 Audit: {agent_sel} ({view_level} View)")
        st.markdown(f"**Focus Period:** {view_level} Analysis")
        st.markdown("---")

        # KPIs (Igual que antes, pero df_final ahora es el periodo completo)
        total_calls = len(df_final)
        talk_secs = df_final['Talk_Secs'].sum()
        idle_secs = df_final['Idle_Secs'].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Calls", total_calls)
        c2.metric("Talk Time", format_seconds(talk_secs))
        c3.metric("Idle Time", format_seconds(idle_secs))
        c4.metric("Avg Talk/Call", f"{int(talk_secs/total_calls) if total_calls > 0 else 0}s")

        st.markdown("---")

        # VISUALES DINÁMICOS
        col_donut, col_trend = st.columns([1, 2])

        with col_donut:
            st.subheader("Time Distribution")
            fig_pie = px.pie(names=['Talk', 'Idle'], values=[talk_secs, idle_secs], hole=0.5,
                             color_discrete_sequence=['#0066cc', '#E5E7E9'])
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_trend:
            if view_level == "Daily":
                st.subheader("Intraday Activity Pulse")
                fig = px.timeline(df_final, x_start="Inicio_Mx", x_end="Fin_Mx", y="Full_Name", color_discrete_sequence=['#0066cc'])
                fig.update_layout(yaxis_visible=False, height=250)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.subheader("Daily Performance Trend")
                # Agrupamos por día para ver cómo se comportó en la semana/mes/Q
                trend_data = df_final.groupby('Date_Only').agg({'call_id':'count', 'Talk_Secs':'sum'}).reset_index()
                fig = px.bar(trend_data, x='Date_Only', y='call_id', labels={'call_id':'Calls per Day'},
                             color_discrete_sequence=['#0066cc'], title="Daily Call Volume")
                st.plotly_chart(fig, use_container_width=True)

        # TABLA DE AUDITORÍA
        with st.expander("📄 View Period Log"):
            st.dataframe(df_final[['Date_Only', 'Inicio_Mx', 'Fin_Mx', 'Talk_Formatted', 'external_number', 'Idle_Secs']].sort_values('Inicio_Mx'))
    else:
        st.warning("No data found for this selection.")
