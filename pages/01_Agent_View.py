# v 1.3 - The "form" update
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from data_engine import load_and_process, format_seconds

# 1. Configuración de página
st.set_page_config(page_title="Agent Audit Deep-Dive", layout="wide")

# 2. Carga de datos (Motor compartido)
data = load_and_process()

if data is not None and not data.empty:
    # --- BARRA LATERAL ---
    st.sidebar.header("Filter Engine")
    agent_list = sorted(data['Full_Name'].unique())
    agent_sel = st.sidebar.selectbox("Select Agent", agent_list)
    
    agent_data = data[data['Full_Name'] == agent_sel]
    date_sel = st.sidebar.date_input("Audit Date", agent_data['Date_Only'].max())
    
    # --- PROCESAMIENTO DE VISTA INDIVIDUAL ---
    df_audit = agent_data[agent_data['Date_Only'] == date_sel].copy()

    if not df_audit.empty:
        st.title(f"👤 Performance Audit: {agent_sel}")
        st.markdown(f"**Date:** {date_sel} | **Shift:** Outbound Operations")
        st.markdown("---")

        # --- FILA 1: KPIs RESUMEN ---
        # Calculamos totales del día para este agente
        total_calls = len(df_audit)
        sum_talk_secs = df_audit['Talk_Secs'].sum()
        sum_idle_secs = df_audit['Idle_Secs'].iloc[0] if 'Idle_Secs' in df_audit.columns else 0
        # Re-calculamos el Idle total para asegurar (SOS + Between + EOS)
        # Nota: En el engine ya lo sumamos, así que tomamos el valor del registro
        total_accounted = sum_talk_secs + df_audit['Idle_Secs'].sum() 

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Calls", total_calls)
        kpi1.caption("Dialed Outbound")
        
        kpi2.metric("Total Talk Time", format_seconds(sum_talk_secs))
        kpi2.caption("Active Conversation")
        
        kpi3.metric("Total Idle Time", format_seconds(df_audit['Idle_Secs'].sum()))
        kpi3.caption("Waiting / Gaps")
        
        kpi4.metric("Shift Coverage", format_seconds(total_accounted))
        kpi4.caption("Time Accounted (Talk + Idle)")

        st.markdown("---")

        # --- FILA 2: VISUAL INSIGHTS ---
        col_chart, col_details = st.columns([1, 1])

        with col_chart:
            st.subheader("Time Distribution")
            # Gráfico de Dona para ver el balance del día
            labels = ['Talk Time', 'Idle Time']
            values = [sum_talk_secs, df_audit['Idle_Secs'].sum()]
            
            fig_donut = px.pie(
                names=labels, 
                values=values, 
                hole=0.6,
                color_discrete_sequence=['#0066cc', '#E5E7E9'],
                template="plotly_white"
            )
            fig_donut.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_donut, use_container_width=True)

        with col_details:
            st.subheader("Shift Edge Analysis")
            # Mostramos el GAP de entrada y salida
            sos_val = df_audit[df_audit['is_first']]['SOS_Idle'].sum()
            eos_val = df_audit[df_audit['is_last']]['EOS_Idle'].sum()
            
            st.info(f"**Start of Shift Gap (SOS):** {format_seconds(sos_val)}")
            st.caption("Time from 7/8 AM until first call.")
            
            st.warning(f"**End of Shift Gap (EOS):** {format_seconds(eos_val)}")
            st.caption("Time from last call until 4/5 PM.")
            
            st.success(f"**Average Talk per Call:** {int(sum_talk_secs/total_calls) if total_calls > 0 else 0} seconds")

        # --- FILA 3: PERSONAL PULSE MONITOR ---
        st.markdown("---")
        st.subheader("Activity Pulse (Personal Timeline)")
        
        # Re-formateamos para el gráfico personal
        df_audit['Detail_Label'] = "Call to: " + df_audit['external_number'].astype(str)
        
        fig_pulse = px.timeline(
            df_audit, 
            x_start="Inicio_Mx", 
            x_end="Fin_Mx", 
            y="Full_Name", 
            color_discrete_sequence=['#0066cc'],
            hover_data={"Inicio_Mx": "|%H:%M:%S", "Fin_Mx": "|%H:%M:%S", "Talk_Formatted": True}
        )
        
        fig_pulse.update_layout(
            height=250, 
            showlegend=False, 
            xaxis_title="Time of Day",
            yaxis_visible=False, # Ocultamos el nombre ya que es obvio
            margin=dict(t=20, b=20, l=20, r=20)
        )
        
        fig_pulse.update_xaxes(dtick=3600000, tickformat="%H:%M", showgrid=True)
        st.plotly_chart(fig_pulse, use_container_width=True)

        # --- FILA 4: DATA AUDIT TABLE ---
        with st.expander("📄 View Raw Call Log"):
            st.dataframe(
                df_audit[['Inicio_Mx', 'Fin_Mx', 'Talk_Formatted', 'external_number', 'In_Between_Idle']].sort_values('Inicio_Mx'),
                use_container_width=True
            )

    else:
        st.warning(f"No records found for {agent_sel} on {date_sel}.")
else:
    st.error("Engine failed to load data.")
