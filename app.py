# v 4.3

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. Configuración de la página
st.set_page_config(page_title="HITL Performance Center", layout="wide")

# Función para convertir segundos a formato HH:MM:SS
def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0:
        return "00:00:00"
    return str(timedelta(seconds=int(seconds)))

# --- SEGURIDAD: SIMPLE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.sidebar.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.sidebar.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        st.sidebar.error("❌ Incorrect Password")
        return False
    else:
        return True

def password_entered():
    # Contraseña personalizada
    if st.session_state["password"] == "TruckSmarter2026":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

if check_password():
    # --- CARGA Y TRANSFORMACIÓN DE DATOS (ETL) ---
    @st.cache_data(show_spinner="Updating Activity Metrics...")
    def load_data():
        SHEET_ID = '1fc2KZftpvGLRxAqb8VaT1S2cV1VuVA83ZwXKWWkuLLk'
        GID_DB = '0' # DB_Dialpad
        GID_DIM = '1947121871' # DIM_Agents
        
        url_db = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DB}'
        url_dim = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DIM}'
        
        try:
            df = pd.read_csv(url_db)
            dim = pd.read_csv(url_dim)
            if df.empty: return None
        except: return None

        df.columns = df.columns.str.strip()
        dim.columns = dim.columns.str.strip()

        # Merge con DIM_Agents para traer el Full_Name y Production Floor
        # Usamos 'email' de Dialpad vs 'Master_Email' de tu DIM
        df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor']], 
                      left_on='email', right_on='Master_Email', how='left')

        # Conversión de Tiempos
        df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
        df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')
        df['production_floor'] = pd.to_datetime(df['production_floor'], errors='coerce')

        # Lógica de Horario México (Fixed DST)
        def get_offset(dt):
            if pd.isna(dt): return 2
            year = dt.year
            first_march = datetime(year, 3, 1)
            days_to_sun = (6 - first_march.weekday()) % 7
            dst_start = first_march + timedelta(days=days_to_sun + 7, hours=2)
            first_nov = datetime(year, 11, 1)
            days_to_nov_sun = (6 - first_nov.weekday()) % 7
            dst_end = first_nov + timedelta(days=days_to_nov_sun, hours=2)
            return 1 if dst_start <= dt < dst_end else 2

        df['Offset'] = df['date_started'].apply(get_offset)
        df['Inicio_Mx'] = df['date_started'] + pd.to_timedelta(df['Offset'], unit='h')
        df['Fin_Mx'] = df['date_ended'] + pd.to_timedelta(df['Offset'], unit='h')
        
        # Filtrar por Floor Production Date
        df = df[df['Inicio_Mx'] >= df['production_floor']].copy()
        
        # Duración real de voz (talk_duration en minutos a segundos)
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        df['Talk_Formatted'] = df['Talk_Secs'].apply(format_seconds)

        # Cálculo de Inactividad (Idle Time) entre llamadas del mismo día
        df = df.sort_values(['Full_Name', 'Inicio_Mx'])
        df['Prev_End'] = df.groupby(['Full_Name', df['Inicio_Mx'].dt.date])['Fin_Mx'].shift()
        df['Idle_Secs'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
        
        return df

    data = load_data()

    if data is not None:
        # --- UI PRINCIPAL ---
        st.title("🚀 HITL Activity Pulse Monitor")
        st.sidebar.header("Filter Controls")
        
        # Selector de Fecha
        available_dates = sorted(data['Inicio_Mx'].dt.date.dropna().unique(), reverse=True)
        date_sel = st.sidebar.selectbox("Audit Date", available_dates)

        # Filtrado Final (Solo Outbound)
        df_dia = data[(data['Inicio_Mx'].dt.date == date_sel) & 
                      (~data['categories'].str.contains('Inbound', na=False))].copy()

        if not df_dia.empty:
            # --- SECCIÓN DE KPIs ---
            total_calls = len(df_dia)
            top_agent = df_dia['Full_Name'].value_counts().idxmax()
            avg_idle = df_dia.groupby('Full_Name')['Idle_Secs'].sum().mean()

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Total Calls (Outbound)", total_calls)
            kpi2.metric("Top Performer", top_agent)
            kpi3.metric("Avg. Idle Time / Agent", format_seconds(avg_idle))

            # --- PREPARACIÓN DEL GRÁFICO ---
            # Estadísticas por agente para el eje Y
            stats = df_dia.groupby('Full_Name').agg(
                Conn=('date_connected', 'count'),
                Idle=('Idle_Secs', 'sum')
            ).reset_index()

            df_dia = df_dia.merge(stats, on='Full_Name')
            df_dia['Y_Label'] = (
                "<b><span style='color:black; font-size:13px;'>" + df_dia['Full_Name'] + "</span></b>" + 
                "<br><span style='color:#555555; font-size:11px;'>Calls: " + df_dia['Conn'].astype(str) + 
                " | Idle: " + df_dia['Idle'].apply(format_seconds) + "</span>"
            )

            fig = px.timeline(
                df_dia, x_start="Inicio_Mx", x_end="Fin_Mx", y="Y_Label", color="Full_Name",
                hover_data={
                    "Y_Label": False, "Inicio_Mx": "| %H:%M:%S", "Fin_Mx": "| %H:%M:%S", 
                    "Talk_Formatted": True, "external_number": True, "Full_Name": True
                },
                template="plotly_white"
            )

            # Hover en Inglés y Ajustes Visuales
            fig.update_traces(
                hovertemplate="<b>Agent:</b> %{customdata[4]}<br>" +
                              "<b>Started:</b> %{base|%H:%M:%S}<br>" +
                              "<b>Finished:</b> %{x|%H:%M:%S}<br>" +
                              "<b>Talk Duration:</b> %{customdata[2]}<br>" +
                              "<b>Dialed:</b> %{customdata[3]}<extra></extra>"
            )

            fig.update_layout(
                height=650, showlegend=False, 
                paper_bgcolor="#E5E7E9", # Fondo exterior sobrio
                plot_bgcolor="white",    # Cuadro del gráfico blanco
                yaxis_title=None, 
                xaxis_title="<b>Shift Timeline (Hourly Separators)</b>",
                font=dict(color="black")
            )
            fig.update_xaxes(dtick=3600000, tickformat="%H:%M", showgrid=True, gridcolor='rgba(0,0,0,0.1)')
            fig.update_yaxes(autorange="reversed")

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning(f"No activity found for {date_sel}")
    else:
        st.error("Failed to load data. Please check your GIDs and Internet connection.")

    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()
