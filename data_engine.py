# v1.8.2 - Tactical Engine (Bug Fixes)
import streamlit as st
import pandas as pd
from datetime import timedelta, datetime

def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0: return "0:00:00"
    return str(timedelta(seconds=int(seconds)))

def categorize_gap_strategic(seconds, is_max_gap):
    if seconds <= 180: return "Standard Doc"
    if seconds <= 900: return "Micro-Gap"
    if is_max_gap and seconds > 2700: return "Likely Lunch"
    if seconds <= 3600: return "Extended Idle"
    return "Operational Gap"

@st.cache_data(ttl=600)
def load_and_process():
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    try:
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0")
        dim = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1947121871")
        df.columns = df.columns.str.strip(); dim.columns = dim.columns.str.strip()
        
        df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor', 'Controlio_ID']], left_on='email', right_on='Master_Email', how='left')
        df['Full_Name'] = df['Full_Name'].fillna(df['name'])
        
        # Tiempos
        df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
        df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')

        def get_offset(dt):
            if pd.isna(dt): return 2
            year = dt.year
            dst_start = datetime(year, 3, 1) + timedelta(days=((6 - datetime(year, 3, 1).weekday()) % 7) + 7, hours=2)
            dst_end = datetime(year, 11, 1) + timedelta(days=(6 - datetime(year, 11, 1).weekday()) % 7, hours=2)
            return 1 if dst_start <= dt < dst_end else 2
        
        df['Offset'] = df['date_started'].apply(get_offset)
        df['Inicio_Mx'] = df['date_started'] + pd.to_timedelta(df['Offset'], unit='h')
        df['Fin_Mx'] = df['date_ended'] + pd.to_timedelta(df['Offset'], unit='h')
        df['Date_Only'] = df['Inicio_Mx'].dt.date
        
        # Filtros iniciales
        df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()
        df = df.sort_values(['Full_Name', 'Inicio_Mx'])
        
        # --- NUEVA LÓGICA DE DECOYS (A PRUEBA DE ERRORES) ---
        # Forzamos que el número sea string limpio, sin .0 al final
        df['num_str'] = df['external_number'].fillna(0).astype(int).astype(str)
        df['prev_num'] = df.groupby(['Full_Name', 'Date_Only'])['num_str'].shift()
        
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        # Es repeat si es el mismo número Y la llamada fue corta
        df['is_repeat'] = (df['num_str'] == df['prev_num']) & (df['Talk_Secs'] < 20) & (df['Talk_Secs'] > 0)
        
        # Gaps (Cálculo por día)
        df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
        df['In_Between_Idle'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
        
        # El gap máximo ahora se marca SOLO si es el más grande de ESE día para ESE agente
        df['max_gap_day'] = df.groupby(['Full_Name', 'Date_Only'])['In_Between_Idle'].transform('max')
        df['is_max_gap'] = (df['In_Between_Idle'] == df['max_gap_day']) & (df['In_Between_Idle'] > 2700)
        
        df['Gap_Category'] = df.apply(lambda x: categorize_gap_strategic(x['In_Between_Idle'], x['is_max_gap']), axis=1)

        # Dimensiones Temporales
        df['Month'] = df['Inicio_Mx'].dt.month_name()
        df['Quarter'] = 'Q' + df['Inicio_Mx'].dt.quarter.astype(str)
        df['Week_Number'] = df['Inicio_Mx'].dt.isocalendar().week
        df['Week_Label'] = 'W' + df['Week_Number'].astype(str).str.zfill(2)
        
        # Carga de Controlio para Attendance Status
        # ... (Mantén tu función load_controlio y el merge aquí) ...
        
        return df
    except Exception as e:
        st.error(f"Error Engine: {e}"); return None
