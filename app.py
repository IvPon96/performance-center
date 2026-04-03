import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="HITL Performance Center", layout="wide")

# --- SEGURIDAD: SIMPLE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.sidebar.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.sidebar.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        st.sidebar.error("❌ Incorrect Password")
        return False
    else:
        return True

def password_entered():
    # CAMBIA 'TruckSmarter2026' por la contraseña que tú quieras
    if st.session_state["password"] == "TruckSmarter2026":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

if check_password():
    # --- CARGA DE DATOS ---
    @st.cache_data
    def load_data():
        SHEET_ID = '1fc2KZftpvGLRxAqb8VaT1S2cV1VuVA83ZwXKWWkuLLk'
        GID = 395674968
        url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        df['Inicio_Mx'] = pd.to_datetime(df['Inicio_Mx'], errors='coerce')
        df['Fin_Mx'] = pd.to_datetime(df['Fin_Mx'], errors='coerce')
        # Limpieza de inactividad
        df['Time_Elapsed (Secs)'] = pd.to_numeric(df['Time_Elapsed (Secs)'], errors='coerce').fillna(0)
        df['SOS_EOS (Secs)'] = pd.to_numeric(df['SOS_EOS (Secs)'], errors='coerce').fillna(0)
        return df

    df = load_data()

    # --- INTERFAZ ---
    st.title("📊 HITL Performance Center")
    st.markdown("---")

    # Sidebar: Filters
    st.sidebar.header("Control Panel")
    fecha_default = df['Inicio_Mx'].max().date() if not df['Inicio_Mx'].isnull().all() else pd.to_datetime("today").date()
    fecha_sel = st.sidebar.date_input("Audit Date", fecha_default)

    # Filtrado
    df_clean = df[df['categories'].fillna('').str.contains('Inbound', case=False) == False].copy()
    df_dia = df_clean[df_clean['Inicio_Mx'].dt.date == fecha_sel].copy()

    if not df_dia.empty:
        # --- CÁLCULOS PARA KPIs ---
        total_calls = len(df_dia)
        # Agente más activo (por conteo de filas)
        most_active_agent = df_dia['CALC_Full'].value_counts().idxmax()
        # Promedio de inactividad (Time_elapsed + SOS_EOS)
        avg_inactive_secs = (df_dia.groupby('CALC_Full')['Time_Elapsed (Secs)'].sum() + 
                             df_dia.groupby('CALC_Full')['SOS_EOS (Secs)'].sum()).mean()
        avg_inactive_min = avg_inactive_secs / 60

        # --- KPI CARDS ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Calls (Outbound)", total_calls)
        col2.metric("Most Active Agent", most_active_agent)
        col3.metric("Avg. Inactive Time / Agent", f"{avg_inactive_min:.1f} min")

        # --- PREPARACIÓN DE ETIQUETAS DEL GRÁFICO ---
        # Calculamos stats por agente para poner debajo del nombre
        stats_agente = df_dia.groupby('CALC_Full').agg(
            Connected=('date_connected', 'count'),
            Total_Inactive=('Time_Elapsed (Secs)', lambda x: (x.sum() + df_dia.loc[x.index, 'SOS_EOS (Secs)'].sum()) / 60)
        ).reset_index()

        # Unimos stats al dataframe del día para crear el label
        df_dia = df_dia.merge(stats_agente, on='CALC_Full')
        df_dia['Chart_Label'] = (df_dia['CALC_Full'] + 
                                 "<br><span style='font-size:10px; color:gray;'>Conn: " + df_dia['Connected'].astype(str) + 
                                 " | Inactive: " + df_dia['Total_Inactive'].round(1).astype(str) + "m</span>")

        # --- PULSÓMETRO (ENGLISH & WHITE BACKGROUND) ---
        st.subheader(f"Activity Pulse Monitor - {fecha_sel}")
        
        fig = px.timeline(
            df_dia,
            x_start="Inicio_Mx",
            x_end="Fin_Mx",
            y="Chart_Label",
            color="CALC_Full",
            hover_data={"Inicio_Mx": "| %H:%M:%S", "Fin_Mx": "| %H:%M:%S", "Chart_Label": False},
            template="plotly_white"
        )

        fig.update_yaxes(title="Agents Performance Details", autorange="reversed")
        fig.update_xaxes(title="Shift Timeline (24h Format)", tickformat="%H:%M")
        
        # Forzar fondo blanco y borde
        fig.update_layout(
            height=600,
            showlegend=False,
            paper_bgcolor="white", # Fondo exterior
            plot_bgcolor="white",  # Fondo interior
            font=dict(color="black") # Texto en negro para que resalte en el cuadro blanco
        )

        # Mostrar gráfico
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(f"⚠️ No Outbound calls found for {fecha_sel}.")

    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()
