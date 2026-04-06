# v 1.4 - The "time" update
import streamlit as st
import pandas as pd
from datetime import timedelta, datetime

# Función para formatear segundos a HH:MM:SS
def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0: return "0:00:00"
    return str(timedelta(seconds=int(seconds)))

@st.cache_data(ttl=600)
def load_and_process():
    # 1. Identificadores de Google Sheet
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    GID_DB = '0'  
    GID_DIM = '1947121871'
    
    url_db = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DB}"
    url_dim = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DIM}"
    
    try:
        # 2. Carga y Limpieza Básica
        df = pd.read_csv(url_db)
        dim = pd.read_csv(url_dim)
        df.columns = df.columns.str.strip()
        dim.columns = dim.columns.str.strip()
        
        # 3. Join Engine (Email + Name Fallback)
        df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor']], 
                      left_on='email', right_on='Master_Email', how='left')
        
        dim_by_name = dim[['Dialpad_Name', 'Full_Name', 'production_floor']].rename(
            columns={'Full_Name': 'FN_Name', 'production_floor': 'PF_Name'}
        )
        df['name_clean'] = df['name'].fillna('').str.strip().str.lower()
        dim_by_name['Name_Match'] = dim_by_name['Dialpad_Name'].fillna('').str.strip().str.lower()
        df = df.merge(dim_by_name, left_on='name_clean', right_on='Name_Match', how='left')
        
        # Consolidación final de nombres y fechas de inicio
        df['Full_Name'] = df['Full_Name'].fillna(df['FN_Name']).fillna(df['name'])
        df['production_floor'] = pd.to_datetime(df['production_floor'].fillna(df['PF_Name']), errors='coerce')
        
        # 4. Lógica de Tiempos y Horario de Verano (DST)
        df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
        df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')

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
        
        # --- BLOQUE DE DIMENSIONES TEMPORALES (UNIFICADO) ---
        df['Date_Only'] = df['Inicio_Mx'].dt.date
        df['Year'] = df['Inicio_Mx'].dt.year
        df['Month'] = df['Inicio_Mx'].dt.month_name()
        df['Quarter'] = 'Q' + df['Inicio_Mx'].dt.quarter.astype(str)
        
        # ISO Week (W01, W02...)
        df['Week_Number'] = df['Inicio_Mx'].dt.isocalendar().week
        df['Week_Label'] = 'W' + df['Week_Number'].astype(str).str.zfill(2)
        # ----------------------------------------------------

        # 5. Filtros Operativos
        df = df[df['Inicio_Mx'] >= df['production_floor']].copy()
        df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()
        df = df.sort_values(['Full_Name', 'Inicio_Mx'])
        
        # 6. Métricas de Productividad
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        df['Talk_Formatted'] = df['Talk_Secs'].apply(format_seconds)
        df['Shift_Start_Hour'] = df['Offset'].map({1: 7, 2: 8})
        df['Shift_End_Hour'] = df['Offset'].map({1: 16, 2: 17})
        
        # Cálculo de In-Between Idle
        df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
        df['In_Between_Idle'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
        
        # Marcadores de Inicio/Fin de Turno
        df['is_first'] = ~df.duplicated(subset=['Full_Name', 'Date_Only'], keep='first')
        df['is_last'] = ~df.duplicated(subset=['Full_Name', 'Date_Only'], keep='last')
        
        # Cálculos de SOS (Start of Shift) y EOS (End of Shift)
        def calc_sos(row):
            if row['is_first']:
                t_start = datetime.combine(row['Date_Only'], datetime.min.time()) + timedelta(hours=row['Shift_Start_Hour'])
                return max(0, (row['Inicio_Mx'] - t_start).total_seconds())
            return 0

        def calc_eos(row):
            if row['is_last']:
                t_end = datetime.combine(row['Date_Only'], datetime.min.time()) + timedelta(hours=row['Shift_End_Hour'])
                return max(0, (t_end - row['Fin_Mx']).total_seconds())
            return 0

        df['SOS_Idle'] = df.apply(calc_sos, axis=1)
        df['EOS_Idle'] = df.apply(calc_eos, axis=1)
        df['Idle_Secs'] = df['In_Between_Idle'] + df['SOS_Idle'] + df['EOS_Idle']
        
        return df

    except Exception as e:
        st.error(f"Error en el motor de datos: {e}")
        return None
