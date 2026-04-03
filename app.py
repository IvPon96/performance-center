import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# 1. Configuración de la página
st.set_page_config(page_title="HITL Performance Center", layout="wide")

# Función para convertir segundos a formato HH:MM:SS
def format_seconds(seconds):
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
        df['Inicio_Mx'] = pd.to_datetime(df['Inicio_Mx'], errors='coerce')
        df['Fin_Mx'] = pd.to_datetime(df['Fin_Mx'], errors='coerce')
        
        # Calcular duración de la llamada en formato mm:ss para el hover
        df['Duration'] = (df['Fin_Mx'] - df['Inicio_Mx']).dt.total_seconds().fillna(0)
        df['Duration_Formatted'] = df['Duration'].apply(lambda x: f"{int(x//60)}m {int(x%60)}s")
        
        df['Time_Elapsed (Secs)'] = pd.to_numeric(df['Time_Elapsed (Secs)'], errors='coerce').fillna(0)
        df['SOS_EOS (Secs)'] = pd.to_numeric(df['SOS_EOS (Secs)'], errors='coerce').fillna(0)
        return df

    df = load_data()

    # --- INTERFAZ ---
    st.title("📊 HITL Performance Center")
    st.markdown("---")

    # Sidebar: Control Panel
    st.sidebar.header("Control Panel")
    fecha_default = df['Inicio_Mx'].max().date() if not df['Inicio_Mx'].isnull().all() else pd.to_datetime("today").date()
    fecha_sel = st.sidebar.date_input("Audit Date", fecha_default)

    # Filtrado
    df_clean = df[df['categories'].fillna('').str.contains('Inbound', case=False) == False].copy()
    df_dia = df_clean[df_clean['Inicio_Mx'].dt.date == fecha_sel].copy()

    if not df_dia.empty:
        # --- CÁLCULOS PARA KPIs ---
        total_calls = len(df_dia)
        most_active_agent = df_dia['CALC_Full'].value_counts().idxmax()
        
        # Promedio de inactividad formateado a HH:MM:SS
        avg_inactive_secs = (df_dia.groupby('CALC_Full')['Time_Elapsed (Secs)'].sum() + 
                             df_dia.groupby('CALC_Full')['SOS_EOS (Secs)'].sum()).mean()
        avg_inactive_formatted = format_seconds(avg_inactive_secs)

        # --- KPI CARDS ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Calls (Outbound)", total_calls)
        col2.metric("Most Active Agent", most_active_agent)
        col3.metric("Avg. Inactive Time / Agent", avg_inactive_formatted)

        # --- PREPARACIÓN DE ETIQUETAS ---
        stats_agente = df_dia.groupby('CALC_Full').agg(
            Connected=('date_connected', 'count'),
            Total_Inactive=('Time_Elapsed (Secs)', lambda x: (x.sum() + df_dia.loc[x.index, 'SOS_EOS (Secs)'].sum()))
        ).reset_index()

        df_dia = df_dia.merge(stats_agente, on='CALC_Full')
        # Labels del eje Y más oscuros y detallados
        df_dia['Chart_Label'] = (
            "<b>" + df_dia['CALC_Full'] + "</b>" + 
            "<br><span style='color:#333333;'>Calls: " + df_dia['Connected'].astype(str) + 
            " | Idle: " + df_dia['Total_Inactive'].apply(format_seconds) + "</span>"
        )

        # --- PULSÓMETRO (SOBER THEME) ---
        st.subheader(f"Activity Pulse Monitor - {fecha_sel}")
        
        # Definimos los datos del Hover con nombres personalizados
        fig = px.timeline(
            df_dia,
            x_start="Inicio_Mx",
            x_end="Fin_Mx",
            y="Chart_Label",
            color="CALC_Full",
            hover_data={
                "Chart_Label": False,      # Ocultamos el label repetido
                "CALC_Full": True,         # Se renombrará abajo
                "Inicio_Mx": "| %H:%M:%S",
                "Fin_Mx": "| %H:%M:%S",
                "Duration_Formatted": True,
                "external_number": True
            },
            template="plotly_white"
        )

        # Renombrar etiquetas en el hover
        fig.update_traces(
            hovertemplate="<b>Full Name:</b> %{y}<br>" +
                          "<b>Time Started:</b> %{base|%H:%M:%S}<br>" +
                          "<b>Time Finished:</b> %{x|%H:%M:%S}<br>" +
                          "<b>Call Duration:</b> %{customdata[0]}<br>" +
                          "<b>Dialed Number:</b> %{customdata[1]}<extra></extra>"
        )

        # Ajustes estéticos (Sober Look)
        fig.update_yaxes(
            title="Agent Performance Details", 
            autorange="reversed",
            tickfont=dict(color="#1A1A1A", size=12), # Nombres más oscuros
            title_font=dict(color="#000000", size=14)
        )
        fig.update_xaxes(
            title="Shift Timeline (24h Format)", 
            tickformat="%H:%M",
            tickfont=dict(color="#1A1A1A"),
            title_font=dict(color="#000000")
        )
        
        fig.update_layout(
            height=600,
            showlegend=False,
            paper_bgcolor="#F2F2F2", # Gris muy suave (sober background)
            plot_bgcolor="#FFFFFF",  # Fondo de la gráfica blanco para contraste
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(f"⚠️ No Outbound calls found for {fecha_sel}.")

    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()
