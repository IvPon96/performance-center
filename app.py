import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# 1. Configuración de la página
st.set_page_config(page_title="HITL Performance Center", layout="wide")

# Función para convertir segundos a formato HH:MM:SS
def format_seconds(seconds):
    return str(timedelta(seconds=int(seconds)))

# Función para convertir talk_duration (float minutos) a mm:ss
def format_talk_duration(minutes_float):
    try:
        total_seconds = float(minutes_float) * 60
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        return f"{minutes}m {seconds}s"
    except:
        return "0m 0s"

# --- SEGURIDAD ---
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
        
        # Convertir fechas
        df['Inicio_Mx'] = pd.to_datetime(df['Inicio_Mx'], errors='coerce')
        df['Fin_Mx'] = pd.to_datetime(df['Fin_Mx'], errors='coerce')
        
        # Formatear talk_duration para el visual
        df['Talk_Time_Display'] = df['talk_duration'].apply(format_talk_duration)
        
        # Inactividad
        df['Time_Elapsed (Secs)'] = pd.to_numeric(df['Time_Elapsed (Secs)'], errors='coerce').fillna(0)
        df['SOS_EOS (Secs)'] = pd.to_numeric(df['SOS_EOS (Secs)'], errors='coerce').fillna(0)
        return df

    df = load_data()

    # --- INTERFAZ ---
    st.title("📊 HITL Performance Center")
    st.markdown("---")

    st.sidebar.header("Control Panel")
    fecha_default = df['Inicio_Mx'].max().date() if not df['Inicio_Mx'].isnull().all() else pd.to_datetime("today").date()
    fecha_sel = st.sidebar.date_input("Audit Date", fecha_default)

    # Filtrado: Solo Outbound (puedes añadir aquí check de connected si gustas)
    df_clean = df[df['categories'].fillna('').str.contains('Inbound', case=False) == False].copy()
    df_dia = df_clean[df_clean['Inicio_Mx'].dt.date == fecha_sel].copy()

    if not df_dia.empty:
        # --- KPIs ---
        total_calls = len(df_dia)
        most_active_agent = df_dia['CALC_Full'].value_counts().idxmax()
        avg_inactive_secs = (df_dia.groupby('CALC_Full')['Time_Elapsed (Secs)'].sum() + 
                             df_dia.groupby('CALC_Full')['SOS_EOS (Secs)'].sum()).mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Calls (Outbound)", total_calls)
        col2.metric("Most Active Agent", most_active_agent)
        col3.metric("Avg. Inactive Time / Agent", format_seconds(avg_inactive_secs))

        # --- LABELS EJE Y ---
        stats_agente = df_dia.groupby('CALC_Full').agg(
            Connected=('date_connected', 'count'),
            Total_Inactive=('Time_Elapsed (Secs)', lambda x: (x.sum() + df_dia.loc[x.index, 'SOS_EOS (Secs)'].sum()))
        ).reset_index()

        df_dia = df_dia.merge(stats_agente, on='CALC_Full')
        df_dia['Chart_Label'] = (
            "<b>" + df_dia['CALC_Full'] + "</b>" + 
            "<br><span style='color:#1A1A1A;'>Calls: " + df_dia['Connected'].astype(str) + 
            " | Idle: " + df_dia['Total_Inactive'].apply(format_seconds) + "</span>"
        )

        # --- PULSÓMETRO ---
        st.subheader(f"Activity Pulse Monitor - {fecha_sel}")
        
        # Creamos el gráfico asegurando el orden de custom_data para el hover
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
                "Talk_Time_Display": True,  # customdata[0]
                "external_number": True     # customdata[1]
            },
            template="plotly_white"
        )

        # Corregimos el Hover Template con los nombres correctos
        fig.update_traces(
            hovertemplate="<b>Full Name:</b> %{customdata[2]}<br>" + # Plotly mete CALC_Full aquí
                          "<b>Time Started:</b> %{base|%H:%M:%S}<br>" +
                          "<b>Time Finished:</b> %{x|%H:%M:%S}<br>" +
                          "<b>Call Duration:</b> %{customdata[0]}<br>" +
                          "<b>Dialed Number:</b> %{customdata[1]}<extra></extra>"
        )

        # --- SEPARADORES POR HORA Y ESTILO ---
        fig.update_xaxes(
            title="Shift Timeline (24h Format)", 
            tickformat="%H:%M",
            dtick=3600000, # Una marca cada hora (en milisegundos)
            showgrid=True, 
            gridwidth=1, 
            gridcolor='#EAEAEA', # Gris suave para los separadores
            tickfont=dict(color="#000000")
        )
        
        fig.update_yaxes(
            title="Agent Performance Details", 
            autorange="reversed",
            tickfont=dict(color="#000000", size=12)
        )
        
        fig.update_layout(
            height=600,
            showlegend=False,
            paper_bgcolor="#F8F9FA", # Fondo sobrio
            plot_bgcolor="#FFFFFF",
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(f"⚠️ No Outbound calls found for {fecha_sel}.")

    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()
