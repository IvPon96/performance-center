# v 1.6 - The Controlio update
import streamlit as st
import pandas as pd
from datetime import timedelta, datetime

# --- 1. HELPERS Y CÁLCULOS ---
def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0: return "0:00:00"
    return str(timedelta(seconds=int(seconds)))

def get_attendance_status(login_time, start_shift_hour):
    """Lógica de tu fórmula de Excel para puntualidad"""
    if pd.isna(login_time): return "NO LOG"
    
    # Creamos el objeto tiempo para el inicio de turno (7 u 8 AM)
    shift_start = login_time.replace(hour=start_shift_hour, minute=0, second=0, microsecond=0)
    
    if login_time <= (shift_start + timedelta(seconds=59)):
        return "ON TIME"
    elif login_time <= (shift_start + timedelta(minutes=10)):
        return "TARDY"
    else:
        return "LATE"

# --- 2. MOTOR DE CARGA INDEPENDIENTE (CONTROLIO) ---
@st.cache_data(ttl=600)
def load_controlio():
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    GID_CONTROLIO = '1577581202'
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_CONTROLIO}"
    
    try:
        df_con = pd.read_csv(url)
        df_con.columns = df_con.columns.str.strip().str.lower()
        
        # Convertir fechas (02.01.2026) y horas
        df_con['date_dt'] = pd.to_datetime(df_con['day'], format='%d.%m.%Y').dt.date
        df_con['login_dt'] = pd.to_datetime(df_con['day'] + ' ' + df_con['start_time'], dayfirst=True)
        df_con['logout_dt'] = pd.to_datetime(df_con['day'] + ' ' + df_con['end_time'], dayfirst=True)
        
        return df_con
    except Exception as e:
        st.error(f"Error en Controlio: {e}")
        return None

# --- 3. MOTOR PRINCIPAL (DIALPAD + MERGE CONTROLIO) ---
@st.cache_data(ttl=600)
def load_and_process():
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    GID_DB = '0'  
    GID_DIM = '1947121871'
    
    url_db = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DB}"
    url_dim = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DIM}"
    
    try:
        # Carga básica
        df = pd.read_csv(url_db)
        dim = pd.read_csv(url_dim)
        df.columns = df.columns.str.strip()
        dim.columns = dim.columns.str.strip()
        
        # Join Dialpad + DIM
        df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor', 'Controlio_ID']], 
                      left_on='email', right_on='Master_Email', how='left')
        
        # Fallback de nombre
        dim_by_name = dim[['Dialpad_Name', 'Full_Name', 'production_floor']].rename(
            columns={'Full_Name': 'FN_Name', 'production_floor': 'PF_Name'}
        )
        df['name_clean'] = df['name'].fillna('').str.strip().str.lower()
        dim_by_name['Name_Match'] = dim_by_name['Dialpad_Name'].fillna('').str.strip().str.lower()
        df = df.merge(dim_by_name, left_on='name_clean', right_on='Name_Match', how='left')
        
        df['Full_Name'] = df['Full_Name'].fillna(df['FN_Name']).fillna(df['name'])
        df['production_floor'] = pd.to_datetime(df['production_floor'].fillna(df['PF_Name']), errors='coerce')
        
        # Lógica de Tiempos
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
        df['Date_Only'] = df['Inicio_Mx'].dt.date
        
        # --- INTEGRACIÓN CON CONTROLIO (REFORZADA) ---
        # Inicializamos las columnas como vacías para evitar el KeyError
        df['login_dt'] = pd.NaT
        df['logout_dt'] = pd.NaT
        df['Attendance_Status'] = "NO LOG"
        df['Ready_Gap'] = "0:00:00"
        df['Ready_Gap_Secs'] = 0

        df_con = load_controlio()
        
        if df_con is not None and not df_con.empty:
            # Intentamos la unión
            df = df.drop(columns=['login_dt', 'logout_dt'], errors='ignore') # Limpiamos las temporales
            df = df.merge(
                df_con[['user_name', 'date_dt', 'login_dt', 'logout_dt']],
                left_on=['Controlio_ID', 'Date_Only'],
                right_on=['user_name', 'date_dt'],
                how='left'
            )
            
            # Recalculamos los status solo si hubo match
            df['Attendance_Status'] = df.apply(
                lambda x: get_attendance_status(x['login_dt'], x['Shift_Start_Hour']) if x['is_first'] else None, axis=1
            )
            
            # Cálculo del Ready Gap: $Ready\_Gap = Inicio\_Mx - login\_dt$
            df['Ready_Gap_Secs'] = (df['Inicio_Mx'] - df['login_dt']).dt.total_seconds().fillna(0)
            df['Ready_Gap'] = df['Ready_Gap_Secs'].apply(lambda x: format_seconds(x) if x > 0 else "0:00:00")

        # Dimensiones Temporales
        df['Year'] = df['Inicio_Mx'].dt.year
        df['Month'] = df['Inicio_Mx'].dt.month_name()
        df['Quarter'] = 'Q' + df['Inicio_Mx'].dt.quarter.astype(str)
        df['Week_Number'] = df['Inicio_Mx'].dt.isocalendar().week
        df['Week_Start'] = df['Inicio_Mx'] - pd.to_timedelta(df['Inicio_Mx'].dt.dayofweek, unit='D')
        df['Week_End'] = df['Week_Start'] + pd.to_timedelta(6, unit='D')
        df['Week_Label'] = 'W' + df['Week_Number'].astype(str).str.zfill(2) + " (" + df['Week_Start'].dt.strftime('%b %d') + " - " + df['Week_End'].dt.strftime('%b %d') + ")"

        # Filtros y Cálculos de Productividad
        df = df[df['Inicio_Mx'] >= df['production_floor']].copy()
        df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()
        df = df.sort_values(['Full_Name', 'Inicio_Mx'])
        
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        df['Talk_Formatted'] = df['Talk_Secs'].apply(format_seconds)
        df['Shift_Start_Hour'] = df['Offset'].map({1: 7, 2: 8})
        
        # GAP Analysis (SOS/EOS/Idle)
        df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
        df['In_Between_Idle'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
        df['is_first'] = ~df.duplicated(subset=['Full_Name', 'Date_Only'], keep='first')
        df['is_last'] = ~df.duplicated(subset=['Full_Name', 'Date_Only'], keep='last')
        
        # Aplicamos la lógica de asistencia a la primera llamada de cada día
        df['Attendance_Status'] = df.apply(
            lambda x: get_attendance_status(x['login_dt'], x['Shift_Start_Hour']) if x['is_first'] else None, axis=1
        )
        
        # Ready Gap: Diferencia entre login PC y primera llamada
        df['Ready_Gap_Secs'] = (df['Inicio_Mx'] - df['login_dt']).dt.total_seconds().fillna(0)
        df['Ready_Gap'] = df['Ready_Gap_Secs'].apply(lambda x: format_seconds(x) if x > 0 else "0:00:00")

        # Cálculos de Gaps
        def calc_sos(row):
            if row['is_first']:
                t_start = datetime.combine(row['Date_Only'], datetime.min.time()) + timedelta(hours=row['Shift_Start_Hour'])
                return max(0, (row['Inicio_Mx'] - t_start).total_seconds())
            return 0
        def calc_eos(row):
            if row['is_last']:
                t_end = datetime.combine(row['Date_Only'], datetime.min.time()) + timedelta(hours=row['Offset'].map({1: 16, 2: 17}))
                return max(0, (t_end - row['Fin_Mx']).total_seconds())
            return 0

        df['SOS_Idle'] = df.apply(calc_sos, axis=1)
        df['EOS_Idle'] = df.apply(calc_eos, axis=1)
        df['Idle_Secs'] = df['In_Between_Idle'] + df['SOS_Idle'] + df['EOS_Idle']
        
        return df

    except Exception as e:
        st.error(f"Error en el motor de datos: {e}")
        return None
