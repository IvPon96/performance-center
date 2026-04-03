import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title = "HITL Performance Center", layout = "Wide")

# Función para cargar datos
@st.cache_data
def load_data():
    SHEET_ID: '1fc2KZftpvGLRxAqb8VaT1S2cV1VuVA83ZwXKWWkuLLk'
    GID = 395674968
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df['Inicio_Mx'] = pd.to_datetime(df['Inicio_Mx'], errors='coerce')
    df['Fin_Mx'] = pd.to_datetime(df['Fin_Mx'], errors='coerce')
    return df

# Cargar la data
df = load_data()

# --- INTERFAZ ---
st.title("HITL Performance Center")
st.markdown("---")

#Sidebar: Filters
st.sidebar.header("Configuración de Vista")
fecha_default = df['Inicio_Mx'].max().date() if not df ['Inicio_Mx'].isnull().all() else None
fecha_sel = st.sidebar.date_input("Selecciona el día a auditar", fecha_default)

#Lógica de filtrado
df_clean = df[df['categories'.fillna('').str.contains('Inbound', case=False) == False].copy()
df_dia = df_clean[df_clean['Inicio_Mx'].dt.date == fecha_sel].copy()

# --- Visuals ---
if not df_dia.empty:
  st.subheader(f"Pulsómetro de Actividad - {fecha_sel}")

  fig = px.timeline(
      df_dia,
      x_start = "Inicio_Mx",
      x_end = "Fin_Mx",
      y = "CALC_Full",
      color = "CALC_Full",
      hover_data = {"Inicio_Mx": "| %H:%M:%S", "Fin_Mx": "| %H:$M:%S"},
      template = "Plotly_white"
  )

  fig.update_yaxes(title = "Agentes", autorange = "reversed")
  fig.update_xaxes(title = "Horario", tickformat = "%H:%M")
  fig.update_layout(height = 500, showlegend = False)

  st.plotly_chart(fig, use_container_width=True)

else:
  st.warning("⚠️ No se encontraron llamadas para la fecha seleccionada.")

st.sidebar.info(f"Total registers updated: {len(df)}")
