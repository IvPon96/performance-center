# v 3.3

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
    if st.session_state["password"] == "TruckSmarter2026":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

if check_password():
    # --- CARGA Y TRANSFORMACIÓN DE DATOS ---
    @st.cache_data(show_spinner="Connecting to Database...")
    def load_and_process_data():
        SHEET_ID = '1fc2KZftpvGLRxAqb8VaT1S2cV1VuVA83ZwXKWWkuLLk'
        GID = '395674968' # <--- ASEGÚRATE QUE ESTE GID SEA EL DE DB_DIALPAD
        url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'
        
        try:
            df = pd.read_csv(url)
            if df.empty:
                return None
        except Exception as e:
            return None

        # Limpieza de nombres de columnas
        df.columns = df.columns.str.strip()

        # Verificación de columnas necesarias
        if 'date_started' not in df.columns:
            st.error(f"Column 'date_started' not found. Available columns: {df.columns.tolist()}")
            return None

        # Conversión de tiempos
        df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
        df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')

        # Lógica de México Time (Smart Logic)
        def calculate_offset(dt):
            if pd.isna(dt): return 2
            year = dt.year
            dst_start = datetime(year, 3, 8) + timedelta(days=(6 - datetime(year, 3, 8).weekday()) + 7)
            dst_end = datetime(year, 11, 1) + timedelta(days=(6 - datetime(year, 11, 1).weekday()))
            return 1 if dst_start <= dt < dst_end else 2

        df['Offset'] = df['date_started'].apply(calculate_offset)
        df['Inicio_Mx'] = df['date_started'] + pd.to_timedelta(df['Offset'], unit='h')
        df['Fin_Mx'] = df['date_ended'] + pd.to_timedelta(df['Offset'], unit='h')
        
        # Duración y gaps
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        df['Talk_Formatted'] = df['Talk_Secs'].apply(format_seconds)
        
        # Si estas columnas ya no existen en la Sheet, las creamos en 0 por ahora
        if 'time_elapsed' not in df.columns: df['time_elapsed'] = 0
        if 'sos_eos' not in df.columns: df['sos_eos'] = 0
        
        df['Time_Elapsed (Secs)'] = pd.to_numeric(df['time_elapsed'], errors='coerce').fillna(0)
        df['SOS_EOS (Secs)'] = pd.to_numeric(df['sos_eos'], errors='coerce').fillna(0)
        
        return df

    # Intentar cargar la data
    df = load_and_process_data()

    if df is not None and not df.empty:
        # --- INTERFAZ ---
        st.title("📊 HITL Performance Center")
        st.markdown("---")

        # Sidebar: Control Panel
        st.sidebar.header("Control Panel")
        
        # Fecha por defecto segura
        last_date = df['Inicio_Mx'].max().date() if not df['Inicio_Mx'].isnull().all() else datetime.now().date()
        fecha_sel = st.sidebar.date_input("Audit Date", last_date)

        # Filtrado
        df_clean = df[df['categories'].fillna('').str.contains('Inbound', case=False) == False].copy()
        df_dia = df_clean[df_clean['Inicio_Mx'].dt.date == fecha_sel].copy()

        if not df_dia.empty:
            # KPI CARDS
            total_calls = len(df_dia)
            most_active_agent = df_dia['CALC_Full'].value_counts().idxmax()
            avg_inactive_secs = (df_dia.groupby('CALC_Full')['Time_Elapsed (Secs)'].sum() + 
                                 df_dia.groupby('CALC_Full')['SOS_EOS (Secs)'].sum()).mean()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Calls (Outbound)", total_calls)
            col2.metric("Most Active Agent", most_active_agent)
            col3.metric("Avg. Inactive Time / Agent", format_seconds(avg_inactive_secs))

            # Gráfico (Pulsómetro)
            stats_agente = df_dia.groupby('CALC_Full').agg(
                Connected=('date_connected', 'count'),
                Total_Idle_Secs=('Time_Elapsed (Secs)', lambda x: x.sum() + df_dia.loc[x.index, 'SOS_EOS (Secs)'].sum())
            ).reset_index()

            df_dia = df_dia.merge(stats_agente, on='CALC_Full')
            df_dia['Chart_Label'] = (
                "<b><span style='color:black; font-size:13px;'>" + df_dia['CALC_Full'] + "</span></b>" + 
                "<br><span style='color:#444444; font-size:11px;'>Calls: " + df_dia['Connected'].astype(str) + 
                " | Idle: " + df_dia['Total_Idle_Secs'].apply(format_seconds) + "</span>"
            )

            fig = px.timeline(
                df_dia, x_start="Inicio_Mx", x_end="Fin_Mx", y="Chart_Label", color="CALC_Full",
                hover_data={"Chart_Label": False, "Inicio_Mx": "| %H:%M:%S", "Fin_Mx": "| %H:%M:%S", "Talk_Formatted": True, "external_number": True},
                template="plotly_white"
            )

            fig.update_traces(
                hovertemplate="<b>Agent:</b> %{customdata[0]}<br><b>Started:</b> %{base|%H:%M:%S}<br><b>Finished:</b> %{x|%H:%M:%S}<br><b>Talk:</b> %{customdata[1]}<br><b>Number:</b> %{customdata[2]}<extra></extra>"
            )

            fig.update_layout(height=650, showlegend=False, paper_bgcolor="#E5E7E9", plot_bgcolor="white")
            fig.update_xaxes(dtick=3600000, tickformat="%H:%M", showgrid=True, gridcolor='rgba(0,0,0,0.1)')
            fig.update_yaxes(autorange="reversed")

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"⚠️ No Outbound calls found for {fecha_sel}.")
    else:
        st.error("❌ Data could not be loaded. Please check your GID and ensure Google Sheets is shared correctly.")
        st.info("💡 Tip: Make sure 'DB_Dialpad' is not currently being edited or calculating formulas.")

    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()
