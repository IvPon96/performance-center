# v 4.1

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# --- SETTINGS ---
st.set_page_config(page_title="HITL Control Center", layout="wide")
SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E' # <--- CAMBIA ESTO
GID_DB = '0' # GID de DB_Dialpad (suele ser 0)
GID_DIM = '1947121871' # <--- BUSCA EL GID DE DIM_AGENTS EN LA URL

# --- DST Logic --- 
def get_mexico_time(df):
    def offset_logic(dt):
        if pd.isna(dt): return 2
        year = dt.year
        
        # --- LÓGICA CORREGIDA PARA EL 2DO DOMINGO DE MARZO ---
        # Buscamos el primer domingo de marzo (empezando desde el día 1)
        first_march = datetime(year, 3, 1)
        # weekday() devuelve 0 para Lunes, 6 para Domingo. 
        # (6 - weekday) nos dice cuántos días faltan para el primer domingo
        days_to_first_sun = (6 - first_march.weekday()) % 7
        dst_start = first_march + timedelta(days=days_to_first_sun + 7) # +7 para que sea el SEGUNDO
        
        # --- LÓGICA PARA EL 1ER DOMINGO DE NOVIEMBRE ---
        first_nov = datetime(year, 11, 1)
        days_to_nov_sun = (6 - first_nov.weekday()) % 7
        dst_end = first_nov + timedelta(days=days_to_nov_sun)
        
        # DEBUG: Por si en el futuro quiero ver las fechas en la consola de Streamlit (Manage App)
        # print(f"Year {year}: DST starts {dst_start.date()}, ends {dst_end.date()}")
        
        return 1 if dst_start <= dt < dst_end else 2
    
    # Asegurar que las columnas son datetime antes de aplicar la lógica
    df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
    df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')
    
    # Aplicar el offset
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
