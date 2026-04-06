# v 2.11

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# --- 1. SETTINGS ---
st.set_page_config(page_title="HITL Performance Center", layout="wide")

def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0: return "0:00:00"
    # Convertimos a HH:MM:SS quitando los microsegundos
    return str(timedelta(seconds=int(seconds)))

# --- 2. SECURITY ---
def check_password():
    if "password_correct" not in st.session_state:
        st.sidebar.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.sidebar.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        st.sidebar.error("❌ Incorrect Password")
        return False
    return True

def password_entered():
    if st.session_state["password"] == "TruckSmarter2026":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=600)
def load_and_process():
    # ... (Mantenemos la carga de datos igual hasta el cálculo de Offset) ...
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    GID_DB = '0' 
    GID_DIM = '1947121871'
    
    url_db = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DB}"
    url_dim = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DIM}"
    
    df = pd.read_csv(url_db)
    dim = pd.read_csv(url_dim)
    df.columns = df.columns.str.strip()
    dim.columns = dim.columns.str.strip()
    
    df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor']], 
                  left_on='email', right_on='Master_Email', how='left')
    
    df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
    df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')
    df['production_floor'] = pd.to_datetime(df['production_floor'], errors='coerce')

    def get_offset(dt):
        if pd.isna(dt): return 2
        year = dt.year
        first_march = datetime(year, 3, 1)
        dst_start = first_march + timedelta(days=((6 - first_march.weekday()) % 7) + 7, hours=2)
        first_nov = datetime(year, 11, 1)
        dst_end = first_nov + timedelta(days=(6 - first_nov.weekday()) % 7, hours=2)
        return 1 if dst_start <= dt < dst_end else 2

    df['Offset'] = df['date_started'].apply(get_offset)
    df['Inicio_Mx'] = df['date_started'] + pd.to_timedelta(df['Offset'], unit='h')
    df['Fin_Mx'] = df['date_ended'] + pd.to_timedelta(df['Offset'], unit='h')
    df['Date_Only'] = df['Inicio_Mx'].dt.date
    
    df = df[df['Inicio_Mx'] >= df['production_floor']].copy()
    df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()

    # --- NUEVA LÓGICA DE SOS / EOS ---
    df = df.sort_values(['Full_Name', 'Inicio_Mx'])
    
    # 1. Definir Entrada y Salida Teórica según DST
    # Si Offset es 1 (DST) -> 7am a 4pm. Si es 2 (Standard) -> 8am a 5pm.
    df['Shift_Start_Hour'] = df['Offset'].map({1: 7, 2: 8})
    df['Shift_End_Hour'] = df['Offset'].map({1: 16, 2: 17})

    # 2. Calcular Gaps entre llamadas (In-between)
    df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
    df['In_Between_Idle'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)

    # 3. Calcular SOS (Diferencia en la PRIMERA llamada del día)
    # Identificamos la primera llamada
    df['is_first'] = ~df.duplicated(subset=['Full_Name', 'Date_Only'], keep='first')
    
    def calculate_sos(row):
        if row['is_first']:
            theoretical_start = datetime.combine(row['Date_Only'], datetime.min.time()) + timedelta(hours=row['Shift_Start_Hour'])
            gap = (row['Inicio_Mx'] - theoretical_start).total_seconds()
            return max(0, gap) # Si empezó antes de su hora, es 0 idle
        return 0

    df['SOS_Idle'] = df.apply(calculate_sos, axis=1)

    # 4. Calcular EOS (Diferencia en la ÚLTIMA llamada del día)
    df['is_last'] = ~df.duplicated(subset=['Full_Name', 'Date_Only'], keep='last')

    def calculate_eos(row):
        if row['is_last']:
            theoretical_end = datetime.combine(row['Date_Only'], datetime.min.time()) + timedelta(hours=row['Shift_End_Hour'])
            gap = (theoretical_end - row['Fin_Mx']).total_seconds()
            return max(0, gap) # Si terminó después de su hora, es 0 idle
        return 0

    df['EOS_Idle'] = df.apply(calculate_eos, axis=1)

    # 5. Idle Total = SOS + In-Between + EOS
    df['Idle_Secs'] = df['In_Between_Idle'] + df['SOS_Idle'] + df['EOS_Idle']
    
    df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
    df['Talk_Formatted'] = df['Talk_Secs'].apply(format_seconds)
    
    return df

# --- 4. INTERFAZ ---
if check_password():
    data = load_and_process()
    
    if data is not None and not data.empty:
        st.title("📊 HITL Performance Center")
        st.markdown("---")

        st.sidebar.header("Control Panel")
        max_date = data['Date_Only'].max()
        # Selector tipo Calendario
        date_sel = st.sidebar.date_input("Select Audit Date", max_date)

        df_dia = data[data['Date_Only'] == date_sel].copy()

        if not df_dia.empty:
            # KPIs
            total_calls = len(df_dia)
            most_active = df_dia['Full_Name'].value_counts().idxmax()
            avg_idle = df_dia.groupby('Full_Name')['Idle_Secs'].sum().mean()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Calls (Outbound)", total_calls)
            c2.metric("Top Performer", most_active)
            c3.metric("Avg. Idle Time", format_seconds(avg_idle))

            # Etiquetas en el eje Y (Negrita Forzada)
            stats = df_dia.groupby('Full_Name').agg(
                Conn=('date_connected', 'count'),
                Idle=('Idle_Secs', 'sum')
            ).reset_index()
            df_dia = df_dia.merge(stats, on='Full_Name')
            
            df_dia['Chart_Label'] = (
                "<b>" + df_dia['Full_Name'] + "</b>" + 
                "<br><span style='color:#333333; font-size:11px;'>Calls: " + df_dia['Conn'].astype(str) + 
                " | Idle: " + df_dia['Idle'].apply(format_seconds) + "</span>"
            )

            st.subheader(f"Activity Pulse Monitor - {date_sel}")
            
            fig = px.timeline(
                df_dia, 
                x_start="Inicio_Mx", 
                x_end="Fin_Mx", 
                y="Chart_Label", 
                color="Full_Name", 
                template="plotly_white",
                hover_data={
                    "Chart_Label": False, 
                    "Full_Name": True,        # customdata[0]
                    "Talk_Formatted": True,   # customdata[1] <-- NUEVO FORMATO
                    "external_number": True,  # customdata[2]
                    "Inicio_Mx": False, 
                    "Fin_Mx": False
                }
            )

            # Ajuste de Hover con formato de tiempo
            fig.update_traces(
                hovertemplate="<b>Agent:</b> %{customdata[0]}<br>" +
                              "<b>Time Started:</b> %{base|%H:%M:%S}<br>" +
                              "<b>Time Finished:</b> %{x|%H:%M:%S}<br>" +
                              "<b>Talk Duration:</b> %{customdata[1]}<br>" + # Ya viene formateado
                              "<b>Dialed Number:</b> %{customdata[2]}<extra></extra>"
            )

            # Estética Sobria con Títulos y Negritas
            fig.update_layout(
                height=650, 
                showlegend=False, 
                paper_bgcolor="#E5E7E9", 
                plot_bgcolor="white",
                font=dict(color="black"),
                xaxis_title="<b>Shift Timeline (24h Format)</b>",
                yaxis_title="<b>Agents Performance Details</b>",
                margin=dict(l=20, r=20, t=50, b=80) 
            )

            fig.update_xaxes(
                dtick=3600000, 
                tickformat="%H:%M", 
                showgrid=True, 
                gridcolor='rgba(0,0,0,0.1)',
                tickfont=dict(color="black", size=12, family="Arial Black"),
                side="bottom" # Asegura que las horas estén abajo
            )

            fig.update_yaxes(
                autorange="reversed", 
                tickfont=dict(color="black", size=12),
                title_font=dict(size=14, family="Arial Black")
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No records found for {date_sel}.")
    else:
        st.error("Connection error or empty dataset.")
