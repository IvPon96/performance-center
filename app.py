# v 2.15 - Full Audit & Label Enhancement

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# --- 1. SETTINGS ---
st.set_page_config(page_title="HITL Performance Center", layout="wide")

def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0: return "0:00:00"
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
    GID_DB = '0' 
    GID_DIM = '1947121871'
    
    url_db = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DB}"
    url_dim = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DIM}"
    
    try:
        df = pd.read_csv(url_db)
        dim = pd.read_csv(url_dim)
        df.columns = df.columns.str.strip()
        dim.columns = dim.columns.str.strip()
        
        df = df.merge(dim[['Master_Email', 'Full_Name', 'production_floor']], 
                      left_on='email', right_on='Master_Email', how='left')
        
        df['Full_Name'] = df['Full_Name'].fillna(df['email'])
        
    except Exception as e:
        return None

    df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
    df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')
    df['production_floor'] = pd.to_datetime(df['production_floor'], errors='coerce')

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
    
    df = df[df['Inicio_Mx'] >= df['production_floor']].copy()
    df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()

    # --- LÓGICA DE TIEMPOS ---
    df = df.sort_values(['Full_Name', 'Inicio_Mx'])
    
    # 1. Talk Time
    df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
    df['Talk_Formatted'] = df['Talk_Secs'].apply(format_seconds)

    # 2. Horarios
    df['Shift_Start_Hour'] = df['Offset'].map({1: 7, 2: 8})
    df['Shift_End_Hour'] = df['Offset'].map({1: 16, 2: 17})

    # 3. Gaps
    df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
    df['In_Between_Idle'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)

    # 4. SOS
    df['is_first'] = ~df.duplicated(subset=['Full_Name', 'Date_Only'], keep='first')
    
    def calculate_sos(row):
        if row['is_first']:
            theoretical_start = datetime.combine(row['Date_Only'], datetime.min.time()) + timedelta(hours=row['Shift_Start_Hour'])
            gap = (row['Inicio_Mx'] - theoretical_start).total_seconds()
            return max(0, gap)
        return 0

    df['SOS_Idle'] = df.apply(calculate_sos, axis=1)

    # 5. EOS
    df['is_last'] = ~df.duplicated(subset=['Full_Name', 'Date_Only'], keep='last')

    def calculate_eos(row):
        if row['is_last']:
            theoretical_end = datetime.combine(row['Date_Only'], datetime.min.time()) + timedelta(hours=row['Shift_End_Hour'])
            gap = (theoretical_end - row['Fin_Mx']).total_seconds()
            return max(0, gap)
        return 0

    df['EOS_Idle'] = df.apply(calculate_eos, axis=1)

    # 6. Totales
    df['Idle_Secs'] = df['In_Between_Idle'] + df['SOS_Idle'] + df['EOS_Idle']
    
    return df

# --- 4. INTERFAZ ---
if check_password():
    data = load_and_process()
    
    if data is not None and not data.empty:
        st.title("📊 HITL Performance Center")
        st.markdown("---")

        st.sidebar.header("Control Panel")
        max_date = data['Date_Only'].max()
        date_sel = st.sidebar.date_input("Select Audit Date", max_date)

        df_dia = data[data['Date_Only'] == date_sel].copy()

        if not df_dia.empty:
            # --- KPIs SUPERIORES ---
            total_calls = len(df_dia)
            total_idle_secs = df_dia.groupby('Full_Name')['Idle_Secs'].sum().mean()
            total_talk_secs = df_dia.groupby('Full_Name')['Talk_Secs'].sum().mean()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Calls", total_calls)
            c2.metric("Avg. Idle Time", format_seconds(total_idle_secs))
            c3.metric("Avg. Talk Time", format_seconds(total_talk_secs))
            c4.metric("Total Accounted", format_seconds(total_idle_secs + total_talk_secs))

            # --- AGREGACIÓN PARA ETIQUETAS Y GRÁFICO ---
            stats = df_dia.groupby('Full_Name').agg(
                Conn=('call_id', 'count'),
                Idle_Sum=('Idle_Secs', 'sum'),
                Talk_Sum=('Talk_Secs', 'sum')
            ).reset_index()
            
            df_dia = df_dia.merge(stats, on='Full_Name')
            
            # Nueva etiqueta con Talk Time debajo
            df_dia['Chart_Label'] = (
                "<b>" + df_dia['Full_Name'] + "</b>" + 
                "<br><span style='color:#333333; font-size:10px;'>Calls: " + df_dia['Conn'].astype(str) + "</span>" +
                "<br><span style='color:#333333; font-size:10px;'>Idle: " + df_dia['Idle_Sum'].apply(format_seconds) + "</span>" +
                "<br><span style='color:#0066cc; font-size:10px;'>Talk: " + df_dia['Talk_Sum'].apply(format_seconds) + "</span>"
            )

            st.subheader(f"Activity Pulse Monitor - {date_sel}")
            
            fig = px.timeline(
                df_dia, x_start="Inicio_Mx", x_end="Fin_Mx", y="Chart_Label", color="Full_Name", 
                template="plotly_white",
                hover_data={"Chart_Label": False, "Full_Name": True, "Talk_Formatted": True, "external_number": True}
            )

            fig.update_traces(
                hovertemplate="<b>Agent:</b> %{customdata[0]}<br><b>Started:</b> %{base|%H:%M:%S}<br><b>Finished:</b> %{x|%H:%M:%S}<br><b>Talk:</b> %{customdata[1]}<br><b>Dialed:</b> %{customdata[2]}<extra></extra>"
            )

            fig.update_layout(
                height=650, showlegend=False, paper_bgcolor="#E5E7E9", plot_bgcolor="white",
                xaxis_title="<b>Shift Timeline (24h Format)</b>",
                yaxis_title="<b>Agents Performance Details</b>",
                margin=dict(l=20, r=20, t=50, b=80) 
            )

            fig.update_xaxes(dtick=3600000, tickformat="%H:%M", showgrid=True, gridcolor='rgba(0,0,0,0.1)', tickfont=dict(color="black", size=12, family="Arial Black"))
            fig.update_yaxes(autorange="reversed", tickfont=dict(color="black", size=11))
            
            st.plotly_chart(fig, use_container_width=True)
            
            # --- ESCOTILLA DE INSPECCIÓN (CORREGIDA) ---
            st.sidebar.markdown("---")
            show_debug = st.sidebar.checkbox("🔍 Open the Black Box (Debug View)")

            if show_debug:
                st.markdown("---")
                st.subheader("🕵️ Inside the Machine: Virtual Data Inspection")
                
                # Tabla 1: Conciliación
                st.write("### ⚖️ Shift Reconciliation (Verification)")
                reconciliation = stats.copy()
                reconciliation['Total_Shift'] = reconciliation['Talk_Sum'] + reconciliation['Idle_Sum']
                reconciliation['Talk_Time'] = reconciliation['Talk_Sum'].apply(format_seconds)
                reconciliation['Idle_Time'] = reconciliation['Idle_Sum'].apply(format_seconds)
                reconciliation['Accounted'] = reconciliation['Total_Shift'].apply(format_seconds)
                
                st.table(reconciliation[['Full_Name', 'Talk_Time', 'Idle_Time', 'Accounted']])
                
                # Tabla 2: Auditoría Fila por Fila
                st.write("### 📋 Row-by-Row Internal Calculation")
                debug_cols = [
                    'Full_Name', 'Inicio_Mx', 'Fin_Mx', 
                    'Talk_Secs', 'In_Between_Idle', 'SOS_Idle', 'EOS_Idle',
                    'is_first', 'is_last'
                ]
                st.dataframe(df_dia[debug_cols].sort_values(['Full_Name', 'Inicio_Mx']), use_container_width=True)
        else:
            st.warning(f"No records found for {date_sel}.")
    else:
        st.error("Connection error or empty dataset.")
