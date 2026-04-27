# 📊 Performance Center
Dashboard operativo para equipos BPO construido con Python y Stramlit.
🔗 [Ver app en vivo](https://performance-center-gvypmznhdhc7erc6kuaieb.streamlit.app/)

## El problema
Los datos de la operación vivían en un Google Sheets: Un solo usuario a la vez, lento, y sin visibilidad real sobre cómo los agentes distribuían su tiempo. No había forma de ver —literalmente— qué pasaba entre llamadas.

## ¿Qué hace?
Dos vistas complementarias que juntas da una imagen completa de la operación:

**Operations View (General)**
- Carga de trabajo por intervalos de 15 minutos
- Eficacia del equipo por día
- Mapa de calor de actividad por hora
- Números más marcados por el equipo

**Agent View (Individual)**
- Llamadas por agente por día
- Talk time vs idle time
- Patrones de marcación
- Periodos de desconexión

Ambas vistas comparten la misma lógica de datos con granularidad configurable: día, semana, mes y trimestre. La vista diaria funciona como una lupa; la semanal/mensual/trimestral como la vista completa.
Esto permite implementar KPIs de capacidad operativa basados en tiempo libre real vs carga de trabajo disponible

## Stack
- Python + Streamlit (Visualización)
- Plotly Express (timelines y mapas de calor)
- Google Sheets (base de datos operativa)
- Google Apps Script + Automa (automatización ETL)
- Github + Codespaces (desarrollo y versionamiento)

## Lo que aprendí construyendolo:
La parte más dificil fue hacer que la vista general y la vista individual hablaran el mismo idioma. La solución fue migrar toda la lógica y matemáticas a un 'data_engine.py' centralizado que nutre ambas vistas con los mismos cálculos.

Si lo empezara hoy, comenzaría por definir qué quiero ver antes de escribir una sola línea de código.

## Autor
Iván Ponce - Team leader en transición a Analytics Engineer
[LinkedIn](www.linkedin.com/in/ivan-ponce-rodriguez-8640832ba)

