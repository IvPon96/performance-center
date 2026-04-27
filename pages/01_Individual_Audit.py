# v4.0 - Corporate Portfolio Edition (Individual Execution Audit)
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Individual Execution Audit", layout="wide")

# CSS Minimalista Corporativo (Igual que Global Operations)
st.markdown("""
    <style>
    .stMetric { background-color: #f8f9fa; border-left: 4px solid #1f77b4; padding: 15px; border-radius: 5px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { color: #2c3e50; font-family: 'Helvetica Neue', sans-serif; font-weight: 600; }
    h1, h2, h3 { color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

data_pack = load_and_process()

if data_pack:
    data = data_pack['main']
    
    if not data.empty:
        st.sidebar.header("👤 Audit Parameters")
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
            st.title(f"👤 Individual Execution Audit: {agent_sel}")
            st.markdown("Detailed behavioral tracking and performance timeline.")

            # --- KPI ROW ---
            talk_t = df_final['Talk_Secs'].sum()
            idle_t = df_final['In_Between_Idle'].sum()
            total_redundant = len(df_final[df_final['is_repeat'] == True])
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Productive Talk Time", format_seconds(talk_t))
            c2.metric("Total Idle Time", format_seconds(idle_t))
            c3.metric("Total Executed Tasks", len(df_final))
            c4.metric("Redundant Attempts ⚠️", total_redundant)

            st.markdown("<br><hr><br>", unsafe_allow_html=True)

            # --- ROW 1: DISTRIBUTION & TIMELINE ---
            col_l, col_r = st.columns([1, 1])
            with col_l:
                st.subheader("Time Distribution")
                st.markdown("<span style='font-size:0.9em; color:gray;'>Ratio of productive time vs system idle periods.</span>", unsafe_allow_html=True)
                fig_p = px.pie(names=['Talk Time', 'Idle Time'], values=[talk_t, idle_t], hole=0.6, 
                               color_discrete_sequence=['#1f77b4', '#e9ecef'])
                fig_p.update_layout(height=400, margin=dict(t=30, b=30, l=0, r=0), template='plotly_white')
                st.plotly_chart(fig_p, use_container_width=True)
                
            with col_r:
                st.subheader("📱 Activity Timeline")
                st.markdown("<span style='font-size:0.9em; color:gray;'>Chronological log of system interactions.</span>", unsafe_allow_html=True)
                days = sorted(df_final['Date_Only'].unique(), reverse=True)
                with st.container(height=400):
                    for d in days:
                        d_data = df_final[df_final['Date_Only'] == d]
                        st.markdown(f"**📅 {d.strftime('%A, %b %d')}**")
                        fig_d = px.timeline(d_data, x_start="Inicio_Mx", x_end="Fin_Mx", y="Full_Name", color_discrete_sequence=['#1f77b4'])
                        fig_d.update_layout(height=120, margin=dict(t=5, b=25, l=0, r=10), yaxis_visible=False, 
                                            xaxis=dict(showticklabels=True, dtick=3600000, tickformat="%H:%M", gridcolor='#e9ecef'),
                                            template='plotly_white')
                        st.plotly_chart(fig_d, use_container_width=True, config={'displayModeBar': False})

            st.markdown("<hr>", unsafe_allow_html=True)

            # --- ROW 2: FREQUENCY ---
            st.subheader("📊 Execution Frequency Trend")
            if view_level == "Daily":
                freq_data = df_final.groupby('15m_Interval').size().reset_index(name='Tasks')
                fig_bar = px.bar(freq_data, x='15m_Interval', y='Tasks', color_discrete_sequence=['#2ca02c'])
            else:
                trend_data = df_final.groupby('Date_Only').size().reset_index(name='Tasks')
                fig_bar = px.bar(trend_data, x='Date_Only', y='Tasks', color_discrete_sequence=['#1f77b4'])
            
            fig_bar.update_layout(height=350, template='plotly_white', xaxis=dict(showgrid=False), yaxis=dict(gridcolor='#e9ecef'))
            st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # --- ROW 3: HEALTH & TARGETS ---
            mid_l, mid_r = st.columns([1, 1])
            with mid_l:
                st.subheader("🎯 Operational Health")
                critical_gaps = len(df_final[df_final['Gap_Category'].isin(["Extended Idle", "Operational Gap"])])
                if critical_gaps > 0: 
                    st.warning(f"Detected {critical_gaps} Critical Unexplained Gaps", icon="⚠️")
                st.metric("Critical Gaps (>15m)", critical_gaps, delta="Review Required" if critical_gaps > 0 else "Normal", delta_color="inverse")
                
                doc_df = df_final[df_final['Gap_Category'] == "Standard Doc"]
                avg_doc = doc_df['In_Between_Idle'].mean() if not doc_df.empty else 0
                st.metric("Avg System Documentation Time", f"{int(avg_doc/60)}m {int(avg_doc%60)}s")
                
                has_lunch = "Detected ✅" if "🥗 Likely Lunch" in df_final['Gap_Category'].values else "Not Found ❌"
                st.metric("Scheduled Break Status", has_lunch)

            with mid_r:
                st.subheader("🏢 Most Contacted Entities")
                all_brokers = df_final.groupby(['num_str', 'Broker_Name']).agg({
                    'daily_attempts': 'count',
                    'Talk_Secs': 'sum'
                }).reset_index().sort_values('daily_attempts', ascending=False)
                all_brokers['Talk_Time'] = all_brokers['Talk_Secs'].apply(format_seconds)
                with st.container(height=350):
                    st.dataframe(all_brokers[['Broker_Name', 'num_str', 'daily_attempts', 'Talk_Time']], 
                                 column_config={
                                     "Broker_Name": "Target Entity",
                                     "num_str": "Contact ID",
                                     "daily_attempts": "Total Dials",
                                     "Talk_Time": "Total Talk Time"
                                 }, use_container_width=True, hide_index=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # --- ROW 4: DETAILED LOG (AUDIT MODE) ---
            st.subheader("📋 Detailed Behavioral Log")
            st.markdown("Line-by-line audit trail of agent activity with highlighted operational friction.")
            
            df_log = df_final[['Date_Only', 'Inicio_Mx', 'num_str', 'Broker_Name', 'Talk_Secs', 'In_Between_Idle', 'daily_attempts', 'Gap_Category']].copy()
            df_log['Start'] = df_log['Inicio_Mx'].dt.strftime('%H:%M:%S')
            df_log['Talk'] = df_log['Talk_Secs'].apply(format_seconds)
            df_log['Idle'] = df_log['In_Between_Idle'].apply(format_seconds)
            
            final_table = df_log[['Date_Only', 'Start', 'num_str', 'Broker_Name', 'Talk', 'Idle', 'daily_attempts', 'Gap_Category']].copy()
            final_table.columns = ['Date', 'System Timestamp', 'Contact ID', 'Target Entity', 'Talk Time', 'Idle After', 'Attempt #', 'Operational Status']

            # Tactical styling optimized for light background
            def style_tactical(row):
                styles = [''] * len(row)
                cols = list(final_table.columns)
                
                att = row['Attempt #']
                if att > 5: 
                    styles[cols.index('Attempt #')] = 'background-color: #ffe6e6; color: #cc0000; font-weight: bold;'
                elif att > 2: 
                    styles[cols.index('Attempt #')] = 'color: #d35400; font-weight: bold;' # Dark Orange
                
                cat = row['Operational Status']
                cat_idx = cols.index('Operational Status')
                
                if "Standard Doc" in cat:
                    styles[cat_idx] = 'color: #27ae60;' # Green
                elif "Micro-Gap" in cat:
                    styles[cat_idx] = 'color: #f39c12;' # Amber
                elif "Extended Idle" in cat:
                    styles[cat_idx] = 'color: #e67e22;' # Orange
                elif "Operational Gap" in cat:
                    styles[cat_idx] = 'color: #c0392b; font-weight: bold;' # Red
                elif "🥗 Likely Lunch" in cat:
                    styles[cat_idx] = 'color: #8e44ad; font-weight: bold;' # Purple
                
                return styles

            st.dataframe(final_table.style.apply(style_tactical, axis=1), use_container_width=True, hide_index=True)

        else:
            st.warning("No operational data found for the selected parameters.")
    else:
        st.error("The main dataset is currently empty.")
else:
    st.error("Failed to load Data Pack from the engine.")