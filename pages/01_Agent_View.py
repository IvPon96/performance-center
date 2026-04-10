# 2.9.2 - Final fix
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

            # --- KPI ROW ---
            talk_t = df_final['Talk_Secs'].sum()
            idle_t = df_final['In_Between_Idle'].sum()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Talk Time", format_seconds(talk_t))
            c2.metric("Idle Time", format_seconds(idle_t))
            c3.metric("Total Calls", len(df_final))
            c4.metric("Decoys 🚨", len(df_final[df_final['is_repeat'] == True]))

            st.markdown("---")

            # --- FILA 1: DISTRIBUCIÓN Y FEED ---
            col_l, col_r = st.columns([1, 1])
            with col_l:
                st.subheader("Time Distribution")
                fig_p = px.pie(names=['Talk', 'Idle'], values=[talk_t, idle_t], hole=0.5, color_discrete_sequence=['#0066cc', '#E5E7E9'])
                fig_p.update_layout(height=450, margin=dict(t=30, b=30, l=0, r=0))
                st.plotly_chart(fig_p, use_container_width=True)
            with col_r:
                st.subheader("📱 Activity Feed (Daily Scroll)")
                days = sorted(df_final['Date_Only'].unique(), reverse=True)
                with st.container(height=450):
                    for d in days:
                        d_data = df_final[df_final['Date_Only'] == d]
                        st.markdown(f"**📅 {d.strftime('%A, %b %d')}**")
                        fig_d = px.timeline(d_data, x_start="Inicio_Mx", x_end="Fin_Mx", y="Full_Name", color_discrete_sequence=['#0066cc'])
                        fig_d.update_layout(height=150, margin=dict(t=5, b=35, l=0, r=10), yaxis_visible=False, xaxis=dict(showticklabels=True, dtick=3600000, tickformat="%H:%M"))
                        st.plotly_chart(fig_d, use_container_width=True, config={'displayModeBar': False})

            st.markdown("---")

            # --- FILA 2: FRECUENCIA ---
            st.subheader("📊 Call Frequency Trend")
            if view_level == "Daily":
                freq_data = df_final.groupby('15m_Interval').size().reset_index(name='Calls')
                fig_bar = px.bar(freq_data, x='15m_Interval', y='Calls', color_discrete_sequence=['#00cc96'])
            else:
                trend_data = df_final.groupby('Date_Only').size().reset_index(name='Calls')
                fig_bar = px.bar(trend_data, x='Date_Only', y='Calls', color_discrete_sequence=['#0066cc'])
            fig_bar.update_layout(height=350)
            st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("---")

            # --- FILA 3: SALUD Y BROKERS DIALED ---
            mid_l, mid_r = st.columns([1, 1])
            with mid_l:
                st.subheader("🎯 Operational Health")
                critical_gaps = len(df_final[df_final['Gap_Category'].isin(["Extended Idle", "Operational Gap"])])
                if critical_gaps > 0: st.warning(f"Detected {critical_gaps} Critical Gaps", icon="⚠️")
                st.metric("Gaps Críticos (>15m)", critical_gaps, delta="Review Required" if critical_gaps > 0 else "Normal", delta_color="inverse")
                doc_df = df_final[df_final['Gap_Category'] == "Standard Doc"]
                avg_doc = doc_df['In_Between_Idle'].mean() if not doc_df.empty else 0
                st.metric("Avg Doc Time", f"{int(avg_doc/60)}m {int(avg_doc%60)}s")
                has_lunch = "Detected ✅" if "🥗 Likely Lunch" in df_final['Gap_Category'].values else "Not Found ❌"
                st.metric("Lunch Break Status", has_lunch)

            with mid_r:
                st.subheader("🏢 Brokers Dialed (Contact List)")
                all_brokers = df_final.groupby(['num_str', 'Broker_Name']).agg({
                    'daily_attempts': 'count',
                    'Talk_Secs': 'sum'
                }).reset_index().sort_values('daily_attempts', ascending=False)
                all_brokers['Talk_Time'] = all_brokers['Talk_Secs'].apply(format_seconds)
                with st.container(height=450):
                    st.dataframe(all_brokers[['Broker_Name', 'num_str', 'daily_attempts', 'Talk_Time']], 
                                 column_config={
                                     "Broker_Name": "Broker / Source",
                                     "num_str": "Phone Number",
                                     "daily_attempts": "Total Dials",
                                     "Talk_Time": "Total Talk"
                                 }, use_container_width=True, hide_index=True)

            st.markdown("---")

# --- FILA 4: LOG DETALLADO (AUDIT MODE CON COLORES COMPLETOS) ---
            st.subheader("📋 Detailed Operational Log (Audit Mode)")
            
            # 1. Selección de datos
            df_log = df_final[['Date_Only', 'Inicio_Mx', 'num_str', 'Broker_Name', 'Talk_Secs', 'In_Between_Idle', 'daily_attempts', 'Gap_Category']].copy()
            
            # 2. Formateo de tiempos
            df_log['Start'] = df_log['Inicio_Mx'].dt.strftime('%H:%M:%S')
            df_log['Talk'] = df_log['Talk_Secs'].apply(format_seconds)
            df_log['Idle'] = df_log['In_Between_Idle'].apply(format_seconds)
            
            # 3. Selección y Renombramiento de columnas para la visualización
            final_table = df_log[['Date_Only', 'Start', 'num_str', 'Broker_Name', 'Talk', 'Idle', 'daily_attempts', 'Gap_Category']].copy()
            final_table.columns = ['Date', 'Start', 'Phone', 'Broker', 'Talk', 'Idle After', 'Attempt #', 'Category']

            # 4. FUNCIÓN DE ESTILO TÁCTICO (Restaurada al 100%)
            def style_tactical(row):
                styles = [''] * len(row)
                cols = list(final_table.columns)
                
                # --- Estilo para Intentos (Fricción) ---
                att = row['Attempt #']
                if att > 5: 
                    styles[cols.index('Attempt #')] = 'background-color: rgba(255,0,0,0.2); color: #ff4b4b; font-weight: bold;'
                elif att > 2: 
                    styles[cols.index('Attempt #')] = 'color: #ffa500; font-weight: bold;'
                
                # --- Estilo para Categorías (Gaps) ---
                cat = row['Category']
                cat_idx = cols.index('Category')
                
                if "Standard Doc" in cat:
                    styles[cat_idx] = 'color: #28a745;' # Verde
                elif "Micro-Gap" in cat:
                    styles[cat_idx] = 'color: #ffc107;' # Amarillo/Dorado
                elif "Extended Idle" in cat:
                    styles[cat_idx] = 'color: #fd7e14;' # Naranja
                elif "Operational Gap" in cat:
                    styles[cat_idx] = 'color: #dc3545; font-weight: bold;' # Rojo
                elif "🥗 Likely Lunch" in cat:
                    styles[cat_idx] = 'color: #6f42c1; font-weight: bold;' # Morado
                
                return styles

            # 5. Renderizado final de la tabla
            st.dataframe(final_table.style.apply(style_tactical, axis=1), use_container_width=True, hide_index=True)

        else:
            st.warning("No hay datos para el periodo seleccionado.")
    else:
        st.error("El DataFrame principal está vacío.")
else:
    st.error("Error al cargar el Data Pack desde el Engine.")
