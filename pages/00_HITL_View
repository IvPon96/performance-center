import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Fleet Dashboard", layout="wide")

# CSS para métricas de flota
st.markdown("""
    <style>
    .stMetric { background-color: rgba(0, 102, 204, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #0066cc; }
    </style>
""", unsafe_allow_html=True)

data = load_and_process()

if data is not None and not data.empty:
    st.title("🚢 HITL Fleet Control Center")
    
    # --- FILTROS DE FLOTA ---
    st.sidebar.header("Global Filters")
    view_level = st.sidebar.radio("Analysis Period", ["Daily", "Weekly", "Monthly", "Quarterly"])
    
    # Lógica de filtrado por periodo (reutilizando dimensiones de data_engine)
    if view_level == "Daily":
        target_date = st.sidebar.date_input("Select Date", data['Date_Only'].max())
        df_fleet = data[data['Date_Only'] == target_date].copy()
    elif view_level == "Weekly":
        week_sel = st.sidebar.selectbox("Select Week", sorted(data['Week_Label'].unique(), reverse=True))
        df_fleet = data[data['Week_Label'] == week_sel].copy()
    elif view_level == "Monthly":
        month_sel = st.sidebar.selectbox("Select Month", sorted(data['Month'].unique()))
        df_fleet = data[data['Month'] == month_sel].copy()
    else:
        q_sel = st.sidebar.selectbox("Select Quarter", sorted(data['Quarter'].unique()))
        df_fleet = data[data['Quarter'] == q_sel].copy()

    if not df_fleet.empty:
        # --- CÁLCULOS DE FLOTA ---
        # Adherencia: Accounted (Talk + Idle) / (Días * 9 horas)
        theoretical_secs_per_day = 32400 # 9h
        working_days = df_fleet.groupby('Full_Name')['Date_Only'].nunique()
        total_theoretical = working_days.sum() * theoretical_secs_per_day
        
        total_talk = df_fleet['Talk_Secs'].sum()
        total_idle = df_fleet['In_Between_Idle'].sum()
        accounted_time = total_talk + total_idle
        
        fleet_adherence = (accounted_time / total_theoretical) * 100 if total_theoretical > 0 else 0
        total_repeats = len(df_fleet[df_fleet['is_repeat']])

        # --- KPI ROW ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Fleet Adherence", f"{fleet_adherence:.1f}%")
        k2.metric("Total Fleet Calls", len(df_fleet))
        k3.metric("Fleet Talk Time", format_seconds(total_talk))
        k4.metric("Total Repeats 🚨", total_repeats)

        st.markdown("---")

        # --- RANKING DE AGENTES ---
        st.subheader("🏆 Agent Performance Ranking")
        
        # Agrupamos por agente para el ranking
        ranking = df_fleet.groupby('Full_Name').agg({
            'Talk_Secs': 'sum',
            'In_Between_Idle': 'sum',
            'num_str': 'count',
            'is_repeat': 'sum',
            'Date_Only': 'nunique'
        }).reset_index()

        ranking.columns = ['Agent', 'Talk_S', 'Idle_S', 'Calls', 'Repeats', 'Days']
        
        # Cálculo de adherencia individual en el periodo
        ranking['Adherence'] = ((ranking['Talk_S'] + ranking['Idle_S']) / (ranking['Days'] * 32400)) * 100
        ranking['Talk_Time'] = ranking['Talk_S'].apply(format_seconds)
        
        # Ordenar por Adherencia
        ranking = ranking.sort_values('Adherence', ascending=False)

        # Estilo de tabla de ranking
        def style_ranking(row):
            styles = [''] * len(row)
            # Colorear Adherencia baja
            if row['Adherence'] < 85: styles[ranking.columns.get_loc('Adherence')] = 'color: #dc3545; font-weight: bold;'
            # Colorear Repeats altos
            if row['Repeats'] > 20: styles[ranking.columns.get_loc('Repeats')] = 'background-color: rgba(139, 0, 0, 0.3); color: white;'
            return styles

        st.dataframe(ranking[['Agent', 'Adherence', 'Calls', 'Repeats', 'Talk_Time']].style.apply(style_ranking, axis=1), 
                     use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- HEATMAP DE ACTIVIDAD ---
        st.subheader("🔥 Fleet Activity Heatmap (Calls per Hour)")
        # Creamos una matriz de Agente vs Hora
        heatmap_data = df_fleet.groupby(['Full_Name', 'Hour']).size().reset_index(name='Call_Count')
        
        fig_heat = px.density_heatmap(heatmap_data, x='Hour', y='Full_Name', z='Call_Count',
                                      labels={'Hour': 'Hora (24h)', 'Full_Name': 'Agente', 'Call_Count': 'Llamadas'},
                                      color_continuous_scale='Viridis', text_auto=True)
        fig_heat.update_layout(height=500)
        st.plotly_chart(fig_heat, use_container_width=True)

        # --- REPEAT ANALYSIS ---
        st.markdown("---")
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.subheader("🚨 Top Decoy Offenders")
            fig_repeat = px.bar(ranking.sort_values('Repeats', ascending=False).head(10), 
                                x='Repeats', y='Agent', orientation='h',
                                color='Repeated', color_discrete_sequence=['#8b0000'])
            st.plotly_chart(fig_repeat, use_container_width=True)
            
        with c_right:
            st.subheader("⏱️ Gap Distribution (Global)")
            # Contamos las categorías de gaps de toda la flota
            gap_dist = df_fleet['Gap_Category'].value_counts().reset_index()
            fig_gap = px.pie(gap_dist, names='Gap_Category', values='count', hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_gap, use_container_width=True)

    else:
        st.warning("No data for the selected period.")
else:
    st.error("Engine failure. Please check data_engine.py")
