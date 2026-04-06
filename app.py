v 4.0

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# --- SETTINGS ---
st.set_page_config(page_title="HITL Control Center", layout="wide")
SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E' # <--- CAMBIA ESTO
GID_DB = '0' # GID de DB_Dialpad (suele ser 0)
GID_DIM = '1947121871' # <--- BUSCA EL GID DE DIM_AGENTS EN LA URL

# --- LOGIC ---
def get_mexico_time(df):
    def offset_logic(dt):
        if pd.isna(dt): return 2
        # DST: 2do dom Marzo - 1er dom Nov
        start = datetime(dt.year, 3, 8) + timedelta(days=(6 - datetime(dt.year, 3, 8).weekday()) + 7)
        end = datetime(dt.year, 11, 1) + timedelta(days=(6 - datetime(dt.year, 11, 1).weekday()))
        return 1 if start <= dt < end else 2
    
    df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
    df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')
    df['Offset'] = df['date_started'].apply(offset_logic)
    df['Inicio_Mx'] = df['date_started'] + pd.to_timedelta(df['Offset'], unit='h')
    df['Fin_Mx'] = df['date_ended'] + pd.to_timedelta(df['Offset'], unit='h')
    return df

@st.cache_data(ttl=600)
def load_data():
    url_db = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DB}"
    url_dim = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DIM}"
    
    df = pd.read_csv(url_db).dropna(subset=['call_id'])
    dim = pd.read_csv(url_dim)
    
    # Cruce con DIM_Agents para traer el nombre real y fecha de producción
    # Asumimos que cruzamos por la columna 'email' de Dialpad
    df = df.merge(dim, left_on='email', right_on='Master_Email', how='left')
    
    # Filtro de producción y cálculos
    df = get_mexico_time(df)
    df['production_floor'] = pd.to_datetime(df['production_floor'])
    df = df[df['Inicio_Mx'] >= df['production_floor']]
    
    # Cálculo de Inactividad
    df = df.sort_values(['Full_Name', 'Inicio_Mx'])
    df['Prev_End'] = df.groupby(['Full_Name', df['Inicio_Mx'].dt.date])['Fin_Mx'].shift()
    df['Idle_Secs'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
    
    return df

# --- UI ---
st.title("🚀 HITL Activity Tracker")

try:
    data = load_data()
    selected_date = st.sidebar.date_input("Select Date", data['Inicio_Mx'].max())
    
    # Filtrado Final
    mask = (data['Inicio_Mx'].dt.date == selected_date) & (~data['categories'].str.contains('Inbound', na=False))
    df_plot = data[mask].copy()

    if not df_plot.empty:
        # Gráfico
        fig = px.timeline(df_plot, x_start="Inicio_Mx", x_end="Fin_Mx", y="Full_Name", color="Full_Name", template="plotly_white")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data found for this day.")
        
except Exception as e:
    st.error(f"Waiting for data... Ensure Sheet is Public and GIDs are correct. Error: {e}")
