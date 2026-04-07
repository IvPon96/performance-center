# v1.8 - Operation Strategy Update
import streamlit as st
import pandas as pd
from datetime import timedelta, datetime

# --- HELPERS ---
def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0: return "0:00:00"
    return str(timedelta(seconds=int(seconds)))

def categorize_gap_strategic(seconds, is_max_gap):
    """Categorización táctica del silencio"""
    if seconds <= 180: return "Standard Doc"    # < 3 min
    if seconds <= 900: return "Micro-Gap"       # 3 - 15 min
    
    # Lógica de Lunch: Solo el gap más largo del día si es > 45 min
    if is_max_gap and seconds > 2700: 
        return "Likely Lunch"
    
    if seconds <= 3600: return "Extended Idle"  # 15 min - 1 hora
    return "Operational Gap"                    # > 1 hora (No es lunch)

def get_attendance_status(login_time, start_shift_hour):
    if pd.isna(login_time): return "NO LOG"
    shift_start = login_time.replace(hour=int(start_shift_hour), minute=0, second=0, microsecond=0)
    if login_time <= (shift_start + timedelta(seconds=59)): return "ON TIME"
    elif login_time <= (shift_start + timedelta(minutes=10)): return "TARDY"
    else: return "LATE"

# --- MOTOR DE CARGA ---
@st.cache_data(ttl=600)
def load_controlio():
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    GID_CONTROLIO = '1577581202'
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_CONTROLIO}"
    try:
        df_con = pd.read_csv(url)
        df_con.columns = df_con.columns.str.strip().str.lower()
        df_con['date_dt'] = pd.to_datetime(df_con['day'], format='%d.%m.%Y').dt.date
        df_con['login_dt'] = pd.to_datetime(df_con['day'] + ' ' + df_con['start_time'], dayfirst=True)
        return df_con
    except: return None

@st.cache_data(ttl=600)
def load_and_process():
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    try:
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0")
        dim = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1947121871")
        df.columns = df.columns.str.strip(); dim.columns = dim.columns.str.strip()
        
        # Merge inicial
        df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor', 'Controlio_ID']], left_on='email', right_on='Master_Email', how='left')
        df['Full_Name'] = df['Full_Name'].fillna(df['name'])
        df['production_floor'] = pd.to_datetime(df['production_floor'], errors='coerce')
        
        # Tiempos México
        df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
        def get_offset(dt):
            if pd.isna(dt): return 2
            dst_start = datetime(dt.year, 3, 8); dst_end = datetime(dt.year, 11, 1) # Simplificado para 2026
            return 1 if dst_start <= dt < dst_end else 2
        
        df['Offset'] = df['date_started'].apply(get_offset)
        df['Inicio_Mx'] = df['date_started'] + pd.to_timedelta(df['Offset'], unit='h')
        df['Fin_Mx'] = pd.to_datetime(df['date_ended'], errors='coerce') + pd.to_timedelta(df['Offset'], unit='h')
        df['Date_Only'] = df['Inicio_Mx'].dt.date
        
        # Integración Controlio
        df_con = load_controlio()
        if df_con is not None:
            df = df.merge(df_con[['user_name', 'date_dt', 'login_dt']], left_on=['Controlio_ID', 'Date_Only'], right_on=['user_name', 'date_dt'], how='left')

        # Filtros y Orden
        df = df[df['Inicio_Mx'] >= df['production_floor']].copy()
        df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()
        df = df.sort_values(['Full_Name', 'Inicio_Mx'])
        
        # --- LÓGICA ESTRATÉGICA ---
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        df['Shift_Start_Hour'] = df['Offset'].map({1: 7, 2: 8})
        
        # Gaps
        df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
        df['In_Between_Idle'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
        
        # Detección de Lunch (Gap máximo > 45 min)
        df['max_gap_day'] = df.groupby(['Full_Name', 'Date_Only'])['In_Between_Idle'].transform('max')
        df['is_max_gap'] = (df['In_Between_Idle'] == df['max_gap_day']) & (df['In_Between_Idle'] > 2700)
        
        df['Gap_Category'] = df.apply(lambda x: categorize_gap_strategic(x['In_Between_Idle'], x['is_max_gap']), axis=1)

        # Detección de Decoys (Mismo número, < 20 seg)
        df['prev_num'] = df.groupby(['Full_Name', 'Date_Only'])['external_number'].shift()
        df['is_repeat'] = (df['external_number'] == df['prev_num']) & (df['Talk_Secs'] < 20) & (df['Talk_Secs'] > 0)
        
        # Marcadores Inicio/Fin
        df['is_first'] = ~df.duplicated(subset=['Full_Name', 'Date_Only'], keep='first')
        df['Attendance_Status'] = df.apply(lambda x: get_attendance_status(x['login_dt'], x['Shift_Start_Hour']) if x['is_first'] else None, axis=1)
        
        # Dimensiones Temporales
        df['Month'] = df['Inicio_Mx'].dt.month_name()
        df['Quarter'] = 'Q' + df['Inicio_Mx'].dt.quarter.astype(str)
        df['Week_Number'] = df['Inicio_Mx'].dt.isocalendar().week
        df['Week_Label'] = 'W' + df['Week_Number'].astype(str).str.zfill(2)
        
        return df
    except Exception as e:
        st.error(f"Error: {e}"); return None
