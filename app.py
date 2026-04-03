#v 3.1

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

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
    # --- CARGA DE DATOS ---
    @st.cache_data
    def load_data():
        SHEET_ID = '1fc2KZftpvGLRxAqb8VaT1S2cV1VuVA83ZwXKWWkuLLk'
        GID = 395674968
        url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        # Conversión de tiempos
        df['Inicio_Mx'] = pd.to_datetime(df['Inicio_Mx'], errors='coerce')
        df['Fin_Mx'] = pd.to_datetime(df['Fin_Mx'], errors='coerce')
        
        # talk_duration viene en minutos decimales (0.71), lo pasamos a segundos
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        df['Talk_Formatted'] = df['Talk_Secs'].apply(format_seconds)
        
        # Métricas de inactividad
        df['Time_Elapsed (Secs)'] = pd.to_numeric(df['Time_Elapsed (Secs)'], errors='coerce').fillna(0)
        df['SOS_EOS (Secs)'] = pd.to_numeric(df['SOS_EOS (Secs)'], errors='coerce').fillna(0)
        return df

    df = load_data()

    # --- INTERFAZ ---
    st.title("📊 HITL Performance Center")
    st.markdown("---")

    # Sidebar
    st.sidebar.header("Control Panel")
    fecha_default = df['Inicio_Mx'].max().date() if not df['Inicio_Mx'].isnull().all() else pd.to_datetime("today").date()
    fecha_sel = st.sidebar.date_input("Audit Date", fecha_default)

    # Filtrado (Excluir Inbound)
    df_clean = df[df['categories'].fillna('').str.contains('Inbound', case=False) == False].copy()
    df_dia = df_clean[df_clean['Inicio_Mx'].dt.date == fecha_sel].copy()

    if not df_dia.empty:
        # --- KPI CARDS ---
        total_calls = len(df_dia)
        most_active_agent = df_dia['CALC_Full'].value_counts().idxmax()
        avg_inactive_secs = (df_dia.groupby('CALC_Full')['Time_Elapsed (Secs)'].sum() + 
                             df_dia.groupby('CALC_Full')['SOS_EOS (Secs)'].sum()).mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Calls (Outbound)", total_calls)
        col2.metric("Most Active Agent", most_active_agent)
        col3.metric("Avg. Inactive Time / Agent", format_seconds(avg_inactive_secs))

        # --- LABELS Y ESTADÍSTICAS ---
        stats_agente = df_dia.groupby('CALC_Full').agg(
            Connected=('date_connected', 'count'),
            Total_Idle_Secs=('Time_Elapsed (Secs)', lambda x: x.sum() + df_dia.loc[x.index, 'SOS_EOS (Secs)'].sum())
        ).reset_index()

        df_dia = df_dia.merge(stats_agente, on='CALC_Full')
        
        # Etiqueta del eje Y con formato HTML (Nombre en negrita y negro puro)
        df_dia['Chart_Label'] = (
            "<b><span style='color:black; font-size:13px;'>" + df_dia['CALC_Full'] + "</span></b>" + 
            "<br><span style='color:#444444; font-size:11px;'>Calls: " + df_dia['Connected'].astype(str) + 
            " | Idle: " + df_dia['Total_Idle_Secs'].apply(format_seconds) + "</span>"
        )

        # --- PULSÓMETRO ---
        st.subheader(f"Activity Pulse Monitor - {fecha_sel}")
        
        fig = px.timeline(
            df_dia,
            x_start="Inicio_Mx",
            x_end="Fin_Mx",
            y="Chart_Label",
            color="CALC_Full",
            hover_data={
                "Chart_Label": False,
                "CALC_Full": True,
                "Inicio_Mx": "| %H:%M:%S",
                "Fin_Mx": "| %H:%M:%S",
                "Talk_Formatted": True,
                "external_number": True
            },
            template="plotly_white"
        )

        # Corrección de los Tooltips (Hover)
        fig.update_traces(
            hovertemplate="<b>Full Name:</b> %{customdata[0]}<br>" +
                          "<b>Time Started:</b> %{base|%H:%M:%S}<br>" +
                          "<b>Time Finished:</b> %{x|%H:%M:%S}<br>" +
                          "<b>Talk Duration:</b> %{customdata[1]}<br>" +
                          "<b>Dialed Number:</b> %{customdata[2]}<extra></extra>"
        )

        # Ajustes de Ejes y Separadores de Hora (Grid)
        fig.update_yaxes(
            title="<b>Agent Performance Details</b>", 
            title_font=dict(color="black", size=15),
            autorange="reversed",
            tickfont=dict(color="black") # Forzar nombres en negro
        )
        
        fig.update_xaxes(
            title="<b>Shift Timeline (Hourly Separators)</b>", 
            title_font=dict(color="black", size=15),
            tickformat="%H:%M",
            dtick=3600000, # Separador cada hora exacta
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(0,0,0,0.1)', # Línea gris tenue
            tickfont=dict(color="black")
        )
        
        fig.update_layout(
            height=650,
            showlegend=False,
            paper_bgcolor="#E5E7E9", # Gris sobrio de fondo (tipo Controlio)
            plot_bgcolor="white",    # Fondo del gráfico blanco para resaltar barras
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(f"⚠️ No Outbound calls found for {fecha_sel}.")

    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()
