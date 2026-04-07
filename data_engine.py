# v1.9 - Bulletproof Tactical Engine
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
        # 1. Carga Protegida
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0")
        dim = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1947121871")
        df.columns = df.columns.str.strip(); dim.columns = dim.columns.str.strip()
        
        # 2. Inicialización de Emergencia (Blindaje contra KeyError)
        # Creamos todas las columnas que el UI va a pedir con valores neutros
        cols_needed = ['num_str', 'is_repeat', 'Gap_Category', 'In_Between_Idle', 'Talk_Secs', 'Inicio_Mx', 'Fin_Mx']
        for col in cols_needed:
            if col not in df.columns:
                if 'Secs' in col or 'Idle' in col: df[col] = 0.0
                elif 'is_' in col: df[col] = False
                else: df[col] = "N/A"

        # 3. Merge y Limpieza
        df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor', 'Controlio_ID']], 
                      left_on='email', right_on='Master_Email', how='left')
        df['Full_Name'] = df['Full_Name'].fillna(df['name']).fillna("Unknown Agent")
        
        # 4. Procesamiento de Tiempos
        df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
        df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')

        def get_offset(dt):
            if pd.isna(dt): return 2
            year = dt.year
            dst_start = datetime(year, 3, 8) # Estimación
            dst_end = datetime(year, 11, 1)
            return 1 if dst_start <= dt < dst_end else 2
        
        df['Offset'] = df['date_started'].apply(get_offset)
        df['Inicio_Mx'] = df['date_started'] + pd.to_timedelta(df['Offset'].fillna(2), unit='h')
        df['Fin_Mx'] = df['date_ended'] + pd.to_timedelta(df['Offset'].fillna(2), unit='h')
        df['Date_Only'] = df['Inicio_Mx'].dt.date
        
        # 5. Lógica de Marcación (Decoys) - Limpieza profunda
        # Convertimos external_number a string sin decimales de forma segura
        df['num_str'] = df['external_number'].fillna(0).apply(lambda x: str(int(float(x))) if str(x).replace('.','').isdigit() else str(x))
        
        df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()
        df = df.sort_values(['Full_Name', 'Inicio_Mx'])
        
        # 6. Cálculo de Gaps e Inactividad
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
        df['In_Between_Idle'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
        
        # Identificar Lunch
        df['max_gap_day'] = df.groupby(['Full_Name', 'Date_Only'])['In_Between_Idle'].transform('max')
        df['is_max_gap'] = (df['In_Between_Idle'] == df['max_gap_day']) & (df['In_Between_Idle'] > 2700)
        df['Gap_Category'] = df.apply(lambda x: categorize_gap_strategic(x['In_Between_Idle'], x['is_max_gap']), axis=1)

        # Identificar Repeticiones (Decoys)
        df['prev_num'] = df.groupby(['Full_Name', 'Date_Only'])['num_str'].shift()
        df['is_repeat'] = (df['num_str'] == df['prev_num']) & (df['Talk_Secs'] < 20) & (df['Talk_Secs'] > 0)
        
        # 7. Dimensiones Temporales
        df['Month'] = df['Inicio_Mx'].dt.month_name()
        df['Quarter'] = 'Q' + df['Inicio_Mx'].dt.quarter.astype(str)
        df['Week_Number'] = df['Inicio_Mx'].dt.isocalendar().week
        df['Week_Label'] = 'W' + df['Week_Number'].astype(str).str.zfill(2)
        
        return df
    except Exception as e:
        st.error(f"Error Crítico en Engine: {e}")
        return None
