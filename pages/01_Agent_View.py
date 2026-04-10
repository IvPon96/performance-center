#v2.8 - Audit Mode
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit Center PRO", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 5px; border: 1px solid rgba(255, 255, 255, 0.1); }
    .stDataFrame { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

data_pack = load_and_process()

if data_pack:
    data = data_pack['main']
    if not data.empty:
        st.sidebar.header("👤 Personal Radar")
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
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Talk Time", format_seconds(df_final['Talk_Secs'].sum()))
            c2.metric("Idle Time", format_seconds(df_final['In_Between_Idle'].sum()))
            c3.metric("Total Calls", len(df_final))
            c4.metric("Decoys 🚨", len(df_final[df_final['is_repeat'] == True]))

            st.markdown("---")
            
            # HEATMAP DE ACTIVIDAD
            st.subheader("🔥 Operational Intensity Heatmap")
            heatmap_data = df_final.groupby(['15m_Interval']).size().reset_index(name='Calls')
            fig_heat = px.bar(heatmap_data, x='15m_Interval', y='Calls', color_discrete_sequence=['#00ff00'])
            fig_heat.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_heat, use_container_width=True)

            st.markdown("---")

            # LOG DETALLADO
            st.subheader("📋 Detailed Operational Log (Audit Mode)")
            df_log = df_final[['Date_Only', 'Inicio_Mx', 'num_str', 'Broker_Name', 'Talk_Secs', 'In_Between_Idle', 'daily_attempts', 'Gap_Category']].copy()
            df_log['Start'] = df_log['Inicio_Mx'].dt.strftime('%H:%M:%S')
            df_log['Talk'] = df_log['Talk_Secs'].apply(format_seconds)
            df_log['Idle'] = df_log['In_Between_Idle'].apply(format_seconds)
            
            final_table = df_log[['Date_Only', 'Start', 'num_str', 'Broker_Name', 'Talk', 'Idle', 'daily_attempts', 'Gap_Category']]
            final_table.columns = ['Date', 'Start', 'Phone', 'Broker', 'Talk', 'Idle After', 'Attempt #', 'Category']

            def style_tactical(row):
                styles = [''] * len(row)
                cols = list(final_table.columns)
                att = row['Attempt #']
                if att > 5: styles[cols.index('Attempt #')] = 'background-color: rgba(255,0,0,0.2); color: #ff4b4b; font-weight: bold;'
                elif att > 2: styles[cols.index('Attempt #')] = 'color: #ffa500; font-weight: bold;'
                
                cat = row['Category']
                if "Operational Gap" in cat: styles[cols.index('Category')] = 'color: #dc3545; font-weight: bold;'
                return styles

            st.dataframe(final_table.style.apply(style_tactical, axis=1), use_container_width=True, hide_index=True)
