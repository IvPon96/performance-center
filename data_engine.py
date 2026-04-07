# v2.4 - Strategic Auditor
import streamlit as st
import pandas as pd
from datetime import timedelta, datetime

# --- UTILIDADES ---
def format_seconds(seconds):
    """Convierte segundos a formato HH:MM:SS de forma segura"""
    if pd.isna(seconds) or seconds <= 0: return "0:00:00"
    return str(timedelta(seconds=int(seconds)))

def categorize_gap_strategic(seconds, is_max_gap):
    """Clasificación táctica de los silencios entre llamadas"""
    if seconds <= 180: return "Standard Doc"    # < 3 min
    if seconds <= 900: return "Micro-Gap"       # 3 - 15 min
    # El gap más largo del día si es > 45 min
    if is_max_gap and seconds > 2700: return "🥗 Likely Lunch"
    if seconds <= 3600: return "Extended Idle"  # 15 min - 1 hora
    return "Operational Gap"                    # > 1 hora

# --- MOTOR DE PROCESAMIENTO ---
@st.cache_data(ttl=600)
def load_and_process():
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    try:
        # 1. CARGA DE DATOS
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0")
        dim = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1947121871")
        df.columns = df.columns.str.strip(); dim.columns = dim.columns.str.strip()
        
        # 2. MERGE CON DIM_AGENTS
        df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor', 'Controlio_ID']], 
                      left_on='email', right_on='Master_Email', how='left')
        df['Full_Name'] = df['Full_Name'].fillna(df['name'])
        
        # 3. PROCESAMIENTO DE TIEMPOS (OFFSET MÉXICO)
        df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
        df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')

        def get_offset(dt):
            if pd.isna(dt): return 2
            # DST 2026: Mar 08 - Nov 01
            return 1 if datetime(dt.year, 3, 8) <= dt < datetime(dt.year, 11, 1) else 2
        
        df['Offset'] = df['date_started'].apply(get_offset)
        df['Inicio_Mx'] = df['date_started'] + pd.to_timedelta(df['Offset'], unit='h')
        df['Fin_Mx'] = df['date_ended'] + pd.to_timedelta(df['Offset'], unit='h')
        df['Date_Only'] = df['Inicio_Mx'].dt.date

        # 4. DIMENSIONES TEMPORALES (Quarter, Week, Month)
        df['Month'] = df['Inicio_Mx'].dt.month_name()
        df['Quarter'] = 'Q' + df['Inicio_Mx'].dt.quarter.astype(str)
        df['Week_Number'] = df['Inicio_Mx'].dt.isocalendar().week
        
        # Etiqueta de semana con rango de fechas
        df['Week_Start'] = df['Inicio_Mx'] - pd.to_timedelta(df['Inicio_Mx'].dt.dayofweek, unit='D')
        df['Week_End'] = df['Week_Start'] + pd.to_timedelta(6, unit='D')
        df['Week_Label'] = (
            'W' + df['Week_Number'].astype(str).str.zfill(2) + 
            " (" + df['Week_Start'].dt.strftime('%b %d') + " - " + df['Week_End'].dt.strftime('%b %d') + ")"
        )
        df['Quarter'] = df['Quarter'].fillna("Q-Unknown")
        
        # 5. LÓGICA DE INTERVALOS (15m) Y NÚMEROS
        df['15m_Interval'] = df['Inicio_Mx'].dt.floor('15min').dt.strftime('%H:%M')
        # Limpieza de números para auditoría
        df['num_str'] = df['external_number'].fillna(0).apply(lambda x: str(int(float(x))) if str(x).replace('.','').isdigit() else str(x))
        
        # 6. FILTROS OPERATIVOS
        df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()
        df = df.sort_values(['Full_Name', 'Inicio_Mx'])
        
        # 7. AUDITORÍA DE REPETICIÓN (DECOYS)
        df['prev_num'] = df.groupby(['Full_Name', 'Date_Only'])['num_str'].shift()
        df['is_repeat'] = (df['num_str'] == df['prev_num']) & (df['num_str'] != '0')
        
        # 8. CÁLCULO DE GAPS
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
        df['In_Between_Idle'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
        
        # Identificar Lunch (Gap máximo por día)
        df['max_gap_day'] = df.groupby(['Full_Name', 'Date_Only'])['In_Between_Idle'].transform('max')
        df['is_max_gap'] = (df['In_Between_Idle'] == df['max_gap_day']) & (df['In_Between_Idle'] > 2700)
        df['Gap_Category'] = df.apply(lambda x: categorize_gap_strategic(x['In_Between_Idle'], x['is_max_gap']), axis=1)

        return df

    except Exception as e:
        st.error(f"Error Crítico en el Engine: {e}")
        return None
