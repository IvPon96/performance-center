# v 2.18 - Minor bux fixing
import streamlit as st
import plotly.express as px
from data_engine import load_and_process, format_seconds

st.set_page_config(page_title="HITL Performance Center", layout="wide")

def check_password():
    if "password_correct" not in st.session_state:
        st.sidebar.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.sidebar.text_input("Password", type="password", on_change=password_entered, key="password")
        st.sidebar.error("❌ Incorrect")
        return False
    return True

def password_entered():
    if st.session_state["password"] == "TruckSmarter2026":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

if check_password():
    data = load_and_process()
    
    if data is not None and not data.empty:
        st.title("📊 HITL Performance Center - Fleet Overview")
        st.sidebar.header("Control Panel")
        max_date = data['Date_Only'].max()
        date_sel = st.sidebar.date_input("Audit Date", max_date)
        df_dia = data[data['Date_Only'] == date_sel].copy()

        if not df_dia.empty:
            total_calls = len(df_dia)
            total_idle_secs = df_dia.groupby('Full_Name')['Idle_Secs'].sum().mean()
            total_talk_secs = df_dia.groupby('Full_Name')['Talk_Secs'].sum().mean()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Calls", total_calls)
            c2.metric("Avg. Idle Time", format_seconds(total_idle_secs))
            c3.metric("Avg. Talk Time", format_seconds(total_talk_secs))
            c4.metric("Total Accounted", format_seconds(total_idle_secs + total_talk_secs))

            stats = df_dia.groupby('Full_Name').agg(
                Conn=('call_id', 'count'),
                Idle_Sum=('Idle_Secs', 'sum'),
                Talk_Sum=('Talk_Secs', 'sum')
            ).reset_index()
            df_dia = df_dia.merge(stats, on='Full_Name')
            
            df_dia['Chart_Label'] = (
                "<b>" + df_dia['Full_Name'] + "</b>" + 
                "<br><span style='color:#333333; font-size:10px;'>Calls: " + df_dia['Conn'].astype(str) + "</span>" +
                "<br><span style='color:#333333; font-size:10px;'>Idle: " + df_dia['Idle_Sum'].apply(format_seconds) + "</span>" +
                "<br><span style='color:#0066cc; font-size:10px;'>Talk: " + df_dia['Talk_Sum'].apply(format_seconds) + "</span>"
            )

            fig = px.timeline(df_dia, x_start="Inicio_Mx", x_end="Fin_Mx", y="Chart_Label", color="Full_Name", template="plotly_white",
                              hover_data={"Chart_Label": False, "Full_Name": True, "Talk_Formatted": True, "external_number": True})
            fig.update_layout(height=650, showlegend=False, paper_bgcolor="#E5E7E9", plot_bgcolor="white")
            fig.update_xaxes(dtick=3600000, tickformat="%H:%M", showgrid=True, gridcolor='rgba(0,0,0,0.1)', tickfont=dict(family="Arial Black"))
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
            
            # --- BLACK BOX LOGIC ---
            st.sidebar.markdown("---")
            show_debug = st.sidebar.checkbox("🔍 Open the Black Box")
            if show_debug:
                st.markdown("---")
                st.subheader("🕵️ Inside the Machine")
                recon = stats.copy()
                recon['Accounted'] = (recon['Talk_Sum'] + recon['Idle_Sum']).apply(format_seconds)
                st.table(recon[['Full_Name', 'Accounted']])
        else:
            st.warning("No data.")
