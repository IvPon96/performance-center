import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit Center PRO", layout="wide")

# CSS Estilizado
st.markdown("""
    <style>
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 5px; border: 1px solid rgba(255, 255, 255, 0.1); }
    .stDataFrame { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

data = load_and_process()

if data is not None and not data.empty:
    st.sidebar.header("Operational Control")
    agent_list = sorted(data['Full_Name'].unique())
    agent_sel = st.sidebar.selectbox("Select Agent", agent_list)
    df_agent = data[data['Full_Name'] == agent_sel].copy()
    
    view_level = st.sidebar.radio("Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    elif view_level == "Weekly":
        weeks = sorted(df_agent['Week_Label'].unique(), reverse=True)
        df_final = df_agent[df_agent['Week_Label'] == st.sidebar.selectbox("Select Week", weeks)].copy()
    elif view_level == "Monthly":
        months = sorted(df_agent['Month'].unique())
        df_final = df_agent[df_agent['Month'] == st.sidebar.selectbox("Select Month", months)].copy()
    else:
        df_final = df_agent[df_agent['Quarter'] == st.sidebar.selectbox("Select Quarter", sorted(df_agent['Quarter'].unique()))].copy()

    if not df_final.empty:
        st.title(f"👤 Individual Audit: {agent_sel}")

        # KPI ROW
        talk_t = df_final['Talk_Secs'].sum()
        idle_t = df_final['In_Between_Idle'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Talk Time", format_seconds(talk_t))
        c2.metric("Idle Time", format_seconds(idle_t))
        c3.metric("Total Calls", len(df_final))
        c4.metric("Repeated 🚨", len(df_final[df_final['is_repeat'] == True]))

        st.markdown("---")

        # Visuals
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.subheader("Time Distribution")
            fig_p = px.pie(names=['Talk', 'Idle'], values=[talk_t, idle_t], hole=0.5, color_discrete_sequence=['#0066cc', '#E5E7E9'])
            fig_p.update_layout(height=520, margin=dict(t=50, b=50, l=0, r=0))
            st.plotly_chart(fig_p, use_container_width=True)
        
        with col_r:
            st.subheader("📱 Activity Feed")
            days = sorted(df_final['Date_Only'].unique(), reverse=True)
            with st.container(height=520):
                for d in days:
                    d_data = df_final[df_final['Date_Only'] == d]
                    st.markdown(f"**📅 {d.strftime('%A, %b %d')}**")
                    fig_d = px.timeline(d_data, x_start="Inicio_Mx", x_end="Fin_Mx", y="Full_Name", color_discrete_sequence=['#0066cc'])
                    fig_d.update_layout(height=150, margin=dict(t=5, b=35, l=0, r=10), yaxis_visible=False)
                    st.plotly_chart(fig_d, use_container_width=True, config={'displayModeBar': False})

        st.markdown("---")

        # Log con Doble Columna de Broker
        st.subheader("📋 Detailed Operational Log")
        
        df_log = df_final[['Date_Only', 'Inicio_Mx', 'Fin_Mx', 'num_str', 'Broker_Name', 'Talk_Secs', 'In_Between_Idle', 'Gap_Category', 'is_repeat']].copy()
        df_log['Start'] = df_log['Inicio_Mx'].dt.strftime('%H:%M:%S')
        df_log['Finished'] = df_log['Fin_Mx'].dt.strftime('%H:%M:%S')
        df_log['Talk'] = df_log['Talk_Secs'].apply(format_seconds)
        df_log['Idle'] = df_log['In_Between_Idle'].apply(format_seconds)
        
        final_table = df_log[['Date_Only', 'Start', 'Finished', 'num_str', 'Broker_Name', 'Talk', 'Idle', 'Gap_Category', 'is_repeat']]
        final_table.columns = ['Date', 'Start', 'Finished', 'Phone', 'Broker', 'Talk', 'Idle After', 'Category', 'Repeated']

        def style_rows(row):
            styles = [''] * len(row)
            cols = list(final_table.columns)
            if row['Repeated']: styles[cols.index('Phone')] = 'color: #8b0000; font-weight: bold;'
            cat = row['Category']
            if "Operational Gap" in cat: styles[cols.index('Category')] = 'color: #dc3545; font-weight: bold;'
            return styles

        st.dataframe(final_table.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos para este periodo.")
else:
    st.error("Error al cargar los datos.")
