# v1.0
import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Fleet Dashboard", layout="wide")

# CSS para métricas de flota con el estilo que nos gusta
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
        df_fleet = data[data['Quarter'] == st.sidebar.selectbox("Select Quarter", sorted(data['Quarter'].unique()))].copy()

    if not df_fleet.empty:
        # --- CÁLCULOS ESTRATÉGICOS DE FLOTA ---
        theoretical_secs_per_day = 32400 # 9h de turno
        working_days = df_fleet.groupby('Full_Name')['Date_Only'].nunique()
        total_theoretical = working_days.sum() * theoretical_secs_per_day
        
        total_talk = df_fleet['Talk_Secs'].sum()
        total_idle = df_fleet['In_Between_Idle'].sum()
        accounted_time = total_talk + total_idle
        
        fleet_adherence = (accounted_time / total_theoretical) * 100 if total_theoretical > 0 else 0
        total_repeats = len(df_fleet[df_fleet['is_repeat'] == True])

        # --- KPI ROW ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Fleet Adherence", f"{fleet_adherence:.1f}%")
        k2.metric("Total Fleet Calls", len(df_fleet))
        k3.metric("Fleet Talk Time", format_seconds(total_talk))
        k4.metric("Total Repeats 🚨", total_repeats)

        st.markdown("---")

        # --- RANKING DE PERFORMANCE ---
        st.subheader("🏆 Agent Performance Ranking")
        
        ranking = df_fleet.groupby('Full_Name').agg({
            'Talk_Secs': 'sum',
            'In_Between_Idle': 'sum',
            'num_str': 'count',
            'is_repeat': 'sum',
            'Date_Only': 'nunique'
        }).reset_index()

        ranking.columns = ['Agent', 'Talk_S', 'Idle_S', 'Calls', 'Repeats', 'Days']
        ranking['Adherence'] = ((ranking['Talk_S'] + ranking['Idle_S']) / (ranking['Days'] * 32400)) * 100
        ranking['Talk_Time'] = ranking['Talk_S'].apply(format_seconds)
        ranking = ranking.sort_values('Adherence', ascending=False)

        def style_ranking(row):
            styles = [''] * len(row)
            if row['Adherence'] < 85: styles[1] = 'color: #dc3545; font-weight: bold;'
            if row['Repeats'] > 25: styles[3] = 'color: #8b0000; font-weight: bold;'
            return styles

        st.dataframe(ranking[['Agent', 'Adherence', 'Calls', 'Repeats', 'Talk_Time']].style.apply(style_ranking, axis=1), 
                     use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- VISUALIZACIÓN DE CARGA ---
        col_heat, col_gaps = st.columns([2, 1])
        
        with col_heat:
            st.subheader("🔥 Fleet Activity Heatmap")
            # Usamos la columna Hour que ya calculamos en el engine
            df_fleet['Hour'] = pd.to_datetime(df_fleet['Inicio_Mx']).dt.hour
            heatmap_data = df_fleet.groupby(['Full_Name', 'Hour']).size().reset_index(name='Calls')
            fig_heat = px.density_heatmap(heatmap_data, x='Hour', y='Full_Name', z='Calls', 
                                          color_continuous_scale='Viridis', text_auto=True)
            fig_heat.update_layout(height=450)
            st.plotly_chart(fig_heat, use_container_width=True)
            
        with col_gaps:
            st.subheader("⏱️ Global Gap Distribution")
            gap_dist = df_fleet['Gap_Category'].value_counts().reset_index()
            fig_pie = px.pie(gap_dist, names='Gap_Category', values='count', hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(height=450)
            st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.warning("No hay datos para el periodo seleccionado.")
