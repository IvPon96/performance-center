# v 4.4 

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="HITL Performance Center", layout="wide")

# Helper to format seconds into HH:MM:SS
def format_seconds(seconds):
    if pd.isna(seconds) or seconds <= 0: return "00:00:00"
    return str(timedelta(seconds=int(seconds)))

# --- 2. SECURITY: SIMPLE LOGIN ---
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
    # Password set to: TruckSmarter2026
    if st.session_state["password"] == "TruckSmarter2026":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

# --- 3. DATA ENGINE (ETL) ---
@st.cache_data(ttl=600)
def load_and_process():
    # NEW SHEET IDENTIFIERS
    SHEET_ID = '1lUjfPzxBRQpko3CcNYSAWsEurNvP9hE4c7XAUkxyY3E'
    GID_DB = '1947121871' # DB_Dialpad
    GID_DIM = '0'        # <--- CHANGE THIS TO YOUR DIM_AGENTS GID
    
    url_db = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DB}"
    url_dim = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DIM}"
    
    try:
        df = pd.read_csv(url_db)
        dim = pd.read_csv(url_dim)
    except Exception as e:
        return None

    df.columns = df.columns.str.strip()
    dim.columns = dim.columns.str.strip()
    
    # Merge with Agent Info
    df = df.merge(dim[['CALC_Master', 'Full_Name', 'production_floor']], on='CALC_Master', how='left')
    
    # Date Conversions
    df['date_started'] = pd.to_datetime(df['date_started'], errors='coerce')
    df['date_ended'] = pd.to_datetime(df['date_ended'], errors='coerce')
    df['production_floor'] = pd.to_datetime(df['production_floor'], errors='coerce')

    # DST Logic (Fixed for March 8th)
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
    
    # Filter: Production Floor and Outbound only
    df = df[df['Inicio_Mx'] >= df['production_floor']].copy()
    df = df[~df['categories'].fillna('').str.contains('Inbound', case=False)].copy()

    # Metrics
    df = df.sort_values(['Full_Name', 'Inicio_Mx'])
    df['Prev_End'] = df.groupby(['Full_Name', 'Date_Only'])['Fin_Mx'].shift()
    df['Idle_Secs'] = (df['Inicio_Mx'] - df['Prev_End']).dt.total_seconds().fillna(0)
    df['Talk_Secs'] = pd.to_numeric(df['talk_duration'], errors='coerce').fillna(0) * 60
    
    return df

# --- 4. APP INTERFACE ---
if check_password():
    data = load_and_process()
    
    if data is not None:
        st.title("📊 HITL Performance Center")
        st.markdown("---")

        # Sidebar Filters
        st.sidebar.header("Control Panel")
        available_dates = sorted(data['Date_Only'].unique(), reverse=True)
        date_sel = st.sidebar.selectbox("Select Audit Date", available_dates)

        df_dia = data[data['Date_Only'] == date_sel].copy()

        if not df_dia.empty:
            # --- KPI CARDS ---
            total_calls = len(df_dia)
            most_active = df_dia['Full_Name'].value_counts().idxmax()
            avg_idle = df_dia.groupby('Full_Name')['Idle_Secs'].sum().mean()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Calls (Outbound)", total_calls)
            c2.metric("Most Active Agent", most_active)
            c3.metric("Avg. Idle Time per Agent", format_seconds(avg_idle))

            # --- CHART PREPARATION ---
            stats = df_dia.groupby('Full_Name').agg(
                Conn=('date_connected', 'count'),
                Idle=('Idle_Secs', 'sum')
            ).reset_index()
            
            df_dia = df_dia.merge(stats, on='Full_Name')
            # High Contrast Labels for Y-Axis
            df_dia['Chart_Label'] = (
                "<b><span style='color:black; font-size:13px;'>" + df_dia['Full_Name'] + "</span></b>" + 
                "<br><span style='color:#333333; font-size:11px;'>Calls: " + df_dia['Conn'].astype(str) + 
                " | Idle: " + df_dia['Idle'].apply(format_seconds) + "</span>"
            )

            # --- PULSÓMETRO CHART ---
            st.subheader(f"Activity Pulse Monitor - {date_sel}")
            
            fig = px.timeline(
                df_dia, x_start="Inicio_Mx", x_end="Fin_Mx", y="Chart_Label", color="Full_Name",
                hover_data={
                    "Chart_Label": False, "Full_Name": True, 
                    "Inicio_Mx": "| %H:%M:%S", "Fin_Mx": "| %H:%M:%S", 
                    "Talk_Secs": True, "external_number": True
                },
                template="plotly_white"
            )

            # Custom Hover (English)
            fig.update_traces(
                hovertemplate="<b>Agent:</b> %{customdata[0]}<br>" +
                              "<b>Time Started:</b> %{base|%H:%M:%S}<br>" +
                              "<b>Time Finished:</b> %{x|%H:%M:%S}<br>" +
                              "<b>Talk Duration:</b> %{customdata[1]:.1f}s<br>" +
                              "<b>Dialed Number:</b> %{customdata[2]}<extra></extra>"
            )

            # Styling: Hourly Grid & Sober Colors
            fig.update_layout(
                height=650, showlegend=False, 
                paper_bgcolor="#E5E7E9", # Sober Grey
                plot_bgcolor="white",    # White Plot Area
                margin=dict(l=20, r=20, t=50, b=20),
                font=dict(color="black")
            )
            fig.update_xaxes(
                title="<b>Shift Timeline (Hourly Separators)</b>",
                dtick=3600000, tickformat="%H:%M", 
                showgrid=True, gridcolor='rgba(0,0,0,0.15)',
                tickfont=dict(color="black", size=12)
            )
            fig.update_yaxes(title=None, autorange="reversed", tickfont=dict(color="black"))

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data found for this date.")
    else:
        st.error("Could not connect to the database. Check SHEET_ID and GIDs.")
