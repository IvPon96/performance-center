# v2.4.1 Layout Final & Fix
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="Agent Audit Center PRO", layout="wide")

# CSS para un look premium y consistente
st.markdown("""
    <style>
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 5px; border: 1px solid rgba(255, 255, 255, 0.1); }
    .stDataFrame { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

data = load_and_process()

if data is not None and not data.empty:
    st.sidebar.header("Operational Control")
    agent_sel = st.sidebar.selectbox("Select Agent", sorted(data['Full_Name'].unique()))
    df_agent = data[data['Full_Name'] == agent_sel].copy()
    
    view_level = st.sidebar.radio("Resolution", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    # --- FILTRADO DINÁMICO ---
    if view_level == "Daily":
        date_sel = st.sidebar.date_input("Select Day", df_agent['Date_Only'].max())
        df_final = df_agent[df_agent['Date_Only'] == date_sel].copy()
    elif view_level == "Weekly":
        weeks = sorted(df_agent['Week_Label'].unique(), reverse=True)
        df_final = df_agent[df_agent['Week_Label'] == st.sidebar.selectbox("Select Week", weeks)].copy()
    elif view_level == "Monthly":
        months = sorted(df_agent['Month'].unique())
        df_final = df_agent[df_agent['Month'] == st.sidebar.selectbox("Select Month", months)].copy()
    else: # Quarterly
        quarters = sorted(df_agent['Quarter'].unique())
        df_final = df_agent[df_agent['Quarter'] == st.sidebar.selectbox("Select Quarter", quarters)].copy()

    if not df_final.empty:
        st.title(f"👤 Auditoría de HITL: {agent_sel}")

        # --- KPI ROW SUPERIOR ---
        talk_secs = df_final['Talk_Secs'].sum()
        idle_secs = df_final['In_Between_Idle'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Talk Time", format_seconds(talk_secs))
        c2.metric("Idle Between Calls", format_seconds(idle_secs))
        c3.metric("Total Calls", len(df_final))
        c4.metric("Repeated Numbers 🚨", len(df_final[df_final['is_repeat'] == True]))

        st.markdown("---")

        # --- FILA 1: DISTRIBUCIÓN Y FEED (1:1 Symmetry) ---
        top_left, top_feed = st.columns([1, 1])
        
        with top_left:
            st.subheader("Time Distribution")
            fig_pie = px.pie(names=['Talk', 'Idle'], values=[talk_secs, idle_secs], hole=0.5, 
                             color_discrete_sequence=['#0066cc', '#E5E7E9'])
            # Altura igualada al contenedor del feed
            fig_pie.update_layout(height=520, margin=dict(t=50, b=50, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with top_feed:
            st.subheader("📱 Activity Feed (Daily Scroll)")
            days_in_period = sorted(df_final['Date_Only'].unique(), reverse=True)
            with st.container(height=520): # Altura fija para scroll
                for day in days_in_period:
                    day_data = df_final[df_final['Date_Only'] == day]
                    st.markdown(f"**📅 {day.strftime('%A, %b %d')}**")
                    fig_day = px.timeline(day_data, x_start="Inicio_Mx", x_end="Fin_Mx", y="Full_Name", color_discrete_sequence=['#0066cc'])
                    fig_day.update_layout(
                        height=150, 
                        margin=dict(t=5, b=35, l=0, r=10),
                        yaxis_visible=False,
                        xaxis=dict(showticklabels=True, dtick=3600000, tickformat="%H:%M")
                    )
                    st.plotly_chart(fig_day, use_container_width=True, config={'displayModeBar': False})
                    st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("---")

        # --- FILA 2: TENDENCIA Y SALUD OPERATIVA (2:1 Ratio) ---
        mid_bar, mid_health = st.columns([2, 1])
        
        with mid_bar:
            if view_level == "Daily":
                st.subheader("📊 Frecuencia (15m Intervals)")
                freq_data = df_final.groupby('15m_Interval').size().reset_index(name='Calls')
                fig_metric = px.bar(freq_data, x='15m_Interval', y='Calls', color_discrete_sequence=['#00cc96'])
            else:
                st.subheader("📈 Daily Volume Trend")
                trend_data = df_final.groupby('Date_Only').size().reset_index(name='Calls')
                fig_metric = px.bar(trend_data, x='Date_Only', y='Calls', color_discrete_sequence=['#0066cc'])
            
            fig_metric.update_layout(height=400)
            st.plotly_chart(fig_metric, use_container_width=True)
            
        with mid_health:
            st.subheader("🎯 Operational Health")
            st.write("") # Espaciador visual
            
            crit_cats = ["Extended Idle", "Operational Gap"]
            critical_gaps = len(df_final[df_final['Gap_Category'].isin(crit_cats)])
            
            # --- FIX: Cambiamos st.alert por st.warning (que sí existe) ---
            if critical_gaps > 0:
                st.warning(f"Detected {critical_gaps} Critical Gaps", icon="⚠️")
            
            st.metric("Gaps Críticos (>15m)", critical_gaps, 
                      delta="Review Required" if critical_gaps > 0 else "Normal", 
                      delta_color="inverse")
            
            doc_df = df_final[df_final['Gap_Category'] == "Standard Doc"]
            avg_doc = doc_df['In_Between_Idle'].mean() if not doc_df.empty else 0
            st.metric("Avg Doc Time (Safe)", f"{int(avg_doc/60)}m {int(avg_doc%60)}s")
            
            has_lunch = "Detected ✅" if "🥗 Likely Lunch" in df_final['Gap_Category'].values else "Not Found ❌"
            st.metric("Lunch Break Status", has_lunch)

        st.markdown("---")

        # --- FILA 3: LOG DETALLADO AL FINAL ---
        st.subheader("📋 Detailed Operational Log (Audit Mode)")
        df_log = df_final[['Date_Only', 'Inicio_Mx', 'Fin_Mx', 'num_str', 'Talk_Secs', 'In_Between_Idle', 'Gap_Category', 'is_repeat']].copy()
        df_log['Date'] = df_log['Date_Only'].astype(str)
        df_log['Start'] = df_log['Inicio_Mx'].dt.strftime('%H:%M:%S')
        df_log['Finished'] = df_log['Fin_Mx'].dt.strftime('%H:%M:%S')
        df_log['Talk'] = df_log['Talk_Secs'].apply(format_seconds)
        df_log['Idle After'] = df_log['In_Between_Idle'].apply(format_seconds)
        
        final_table = df_log[['Date', 'Start', 'Finished', 'num_str', 'Talk', 'Idle After', 'Gap_Category', 'is_repeat']]
        final_table.columns = ['Date', 'Start', 'Finished', 'Number', 'Talk', 'Idle After', 'Category', 'Repeated']

        def style_audit_final(row):
            styles = [''] * len(row)
            cols = list(final_table.columns)
            if row['Repeated']: styles[cols.index('Number')] = 'color: #8b0000; font-weight: bold;'
            cat = row['Category']
            if "Standard Doc" in cat: styles[cols.index('Category')] = 'color: #28a745;'
            elif "Micro-Gap" in cat: styles[cols.index('Category')] = 'color: #ffc107;'
            elif "Extended Idle" in cat: styles[cols.index('Category')] = 'color: #fd7e14;'
            elif "Operational Gap" in cat: styles[cols.index('Category')] = 'color: #dc3545; font-weight: bold;'
            elif "🥗 Likely Lunch" in cat: styles[cols.index('Category')] = 'color: #6f42c1; font-weight: bold;'
            return styles

        st.dataframe(final_table.style.apply(style_audit_final, axis=1), use_container_width=True, hide_index=True)

    else:
        st.warning("No data found for this period.")
else:
    st.error("Engine failed to load data.")
