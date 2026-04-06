# v 5.0

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# --- 1. SETTINGS ---
st.set_page_config(page_title="HITL Performance Center", layout="wide")

def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0: return "00:00:00"
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
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    GID_DB = '0' #DB_Dialpad
    GID_DIM = '1947121871' # DIM_Agents
    
    url_db = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DB}"
    url_dim = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DIM}"
    
    try:
        df = pd.read_csv(url_db)
        dim = pd.read_csv(url_dim)
        
        # Limpieza de nombres de columnas
        df.columns = df.columns.str.strip()
        dim.columns = dim.columns.str.strip()
        
        # VERIFICACIÓN DE SEGURIDAD (Si esto falla, el error será claro)
        required_dim = ['Master_Email', 'Full_Name', 'production_floor']
        missing = [col for col in required_dim if col not in dim.columns]
        if missing:
            st.error(f"❌ Missing columns in DIM_Agents: {missing}")
            st.info(f"Columns found: {dim.columns.tolist()}")
            return None

        # Unir Dialpad (columna 'email') con DIM (columna 'Master_Email')
        df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor']], 
                      left_on='email', right_on='Master_Email', how='left')
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

    # Conversión de fechas
    df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
    df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')
    df['production_floor'] = pd.to_datetime(df['production_floor'], errors='coerce')

    # Lógica DST (México)
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
    
    # Filtros: Solo producción y solo Outbound
    df = df[df['Inicio_Mx'] >= df['production_floor']].copy()
    df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()

    # Cálculos de Inactividad
    df = df.sort_values(['Full_Name', 'Inicio_Mx'])
    df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
    df['Idle_Secs'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
    df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
    
    return df

# --- 4. INTERFAZ ---
if check_password():
    data = load_and_process()
    
    if data is not None and not data.empty:
        st.title("📊 HITL Performance Center")
        st.sidebar.header("Control Panel")
        
        dates = sorted(data['Date_Only'].dropna().unique(), reverse=True)
        date_sel = st.sidebar.selectbox("Select Audit Date", dates)
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

            # Preparación de etiquetas
            stats = df_dia.groupby('Full_Name').agg(
                Conn=('date_connected', 'count'),
                Idle=('Idle_Secs', 'sum')
            ).reset_index()
            df_dia = df_dia.merge(stats, on='Full_Name')
            
            df_dia['Chart_Label'] = (
                "<b>" + df_dia['Full_Name'].fillna('Unknown') + "</b>" + 
                "<br><span style='color:#333333; font-size:11px;'>Calls: " + df_dia['Conn'].astype(str) + 
                " | Idle: " + df_dia['Idle'].apply(format_seconds) + "</span>"
            )

            # Gráfico
            fig = px.timeline(df_dia, x_start="Inicio_Mx", x_end="Fin_Mx", y="Chart_Label", color="Full_Name", template="plotly_white")
            fig.update_layout(height=600, showlegend=False, paper_bgcolor="#E5E7E9", plot_bgcolor="white")
            fig.update_xaxes(dtick=3600000, tickformat="%H:%M", showgrid=True, gridcolor='rgba(0,0,0,0.15)')
            fig.update_yaxes(autorange="reversed", title=None)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No records found for this date.")
