# v2.8.1 - Engine con Friction Intelligence (Fixed Temporal Columns)
import streamlit as st
import pandas as pd
from datetime import timedelta, datetime

def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0: return "0:00:00"
    return str(timedelta(seconds=int(seconds)))

def categorize_gap_strategic(seconds, is_max_gap):
    if seconds <= 180: return "Standard Doc"
    if seconds <= 900: return "Micro-Gap"
    if is_max_gap and seconds > 2700: return "🥗 Likely Lunch"
    if seconds <= 3600: return "Extended Idle"
    return "Operational Gap"

@st.cache_data(ttl=300)
def load_and_process():
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    GID_BROKERS = '606737505'
    GID_RETOOL = '407336031' 
    
    try:
        # 1. CARGA DE FUENTES
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0")
        dim = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1947121871")
        
        # Historial Retool
        try:
            retool_hist = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_RETOOL}")
            retool_hist['Load_Count'] = retool_hist['Load_Count'].astype(str).str.extract('(\d+)').astype(float)
            retool_hist['Timestamp'] = pd.to_datetime(retool_hist['Timestamp'].str.replace(' - ', ' '), errors='coerce')
            retool_hist = retool_hist[(retool_hist['Timestamp'].dt.hour >= 7) & (retool_hist['Timestamp'].dt.hour <= 17)].copy()
        except:
            retool_hist = pd.DataFrame()
        
        # Brokers
        try:
            brokers = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_BROKERS}")
            brokers['Clean_Phone'] = brokers['Clean_Phone'].astype(str).str.replace("'", "").str.strip()
            broker_map = brokers.set_index('Clean_Phone')['Broker_Name'].to_dict()
        except:
            broker_map = {}

        df.columns = df.columns.str.strip()
        dim.columns = dim.columns.str.strip()
        
        # 3. MERGE
        df = df.merge(dim[['Master_Email', 'Full_Name']], left_on='email', right_on='Master_Email', how='left')
        df['Full_Name'] = df['Full_Name'].fillna(df['name'])
        
        # 4. TIEMPOS Y OFFSETS
        df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
        df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')

        def get_offset(dt):
            if pd.isna(dt): return 2
            return 1 if datetime(dt.year, 3, 8) <= dt < datetime(dt.year, 11, 1) else 2
        
        df['Offset'] = df['date_started'].apply(get_offset)
        df['Inicio_Mx'] = df['date_started'] + pd.to_timedelta(df['Offset'], unit='h')
        df['Fin_Mx'] = df['date_ended'] + pd.to_timedelta(df['Offset'], unit='h')
        df['Date_Only'] = df['Inicio_Mx'].dt.date

        # 5. DIMENSIONES TEMPORALES (RESTAURADAS)
        df['Month'] = df['Inicio_Mx'].dt.month_name()
        df['Quarter'] = 'Q' + df['Inicio_Mx'].dt.quarter.astype(str)
        df['Week_Number'] = df['Inicio_Mx'].dt.isocalendar().week
        df['Week_Start'] = df['Inicio_Mx'] - pd.to_timedelta(df['Inicio_Mx'].dt.dayofweek, unit='D')
        df['Week_End'] = df['Week_Start'] + pd.to_timedelta(6, unit='D')
        df['Week_Label'] = 'W' + df['Week_Number'].astype(str).str.zfill(2) + " (" + df['Week_Start'].dt.strftime('%b %d') + " - " + df['Week_End'].dt.strftime('%b %d') + ")"
        
        # 6. MAPPING E INTERVALOS
        df['15m_Interval'] = df['Inicio_Mx'].dt.floor('15min').dt.strftime('%H:%M')
        df['num_str'] = df['external_number'].fillna(0).apply(lambda x: str(int(float(x))) if str(x).replace('.','').isdigit() else str(x))
        df['num_str'] = df['num_str'].str.strip()
        df['Broker_Name'] = df['num_str'].map(broker_map).fillna("Unknown / New")
        
        # 7. FILTROS Y FRICCIÓN
        df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()
        df = df.sort_values(['Full_Name', 'Inicio_Mx'])
        
        # Conteo de intentos diarios al mismo número
        df['daily_attempts'] = df.groupby(['Date_Only', 'num_str']).cumcount() + 1
        df['is_repeat'] = df['daily_attempts'] > 1
        
        df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
        df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
        df['In_Between_Idle'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
        
        df['max_gap_day'] = df.groupby(['Full_Name', 'Date_Only'])['In_Between_Idle'].transform('max')
        df['is_max_gap'] = (df['In_Between_Idle'] == df['max_gap_day']) & (df['In_Between_Idle'] > 2700)
        df['Gap_Category'] = df.apply(lambda x: categorize_gap_strategic(x['In_Between_Idle'], x['is_max_gap']), axis=1)

        return {'main': df, 'retool': retool_hist, 'broker_map': broker_map}
    except Exception as e:
        st.error(f"Error Crítico: {e}")
        return None
