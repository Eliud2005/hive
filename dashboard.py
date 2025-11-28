import streamlit as st
import json
from datetime import datetime
import os
import matplotlib.pyplot as plt
from tinydb import TinyDB, Query
from streamlit_autorefresh import st_autorefresh  # 👈 Importar esto

# -------------------------
# CONFIGURACIÓN BÁSICA
# -------------------------
st.set_page_config(
    page_title="Panel de la Reina 🐝",
    page_icon="🐝",
    layout="wide"
)

# 🔁 Refrescar cada 5 segundos
st_autorefresh(interval=5000, key="datarefresh")  # 👈 Aquí, antes de mostrar contenido

db = TinyDB('hive.json')
query = Query()

st.title("👑 Panel de la Reina - BeeCode")
st.subheader("Monitoreo del enjambre y archivos observados")

# -------------------------
# ESTADÍSTICAS PRINCIPALES
# -------------------------
total_agentes = len(set([r['agent'] for r in db.all()]))
total_reportes = len(db)
archivos_monitoreados = len(set([r.get('file', 'Desconocido') for r in db.all() if 'file' in r]))
archivos_cuarentena = len([f for f in os.listdir('quarantine')]) if os.path.exists('quarantine') else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("🐝 Abejas activas", total_agentes)
col2.metric("📂 Archivos monitoreados", archivos_monitoreados)
col3.metric("🚨 Reportes totales", total_reportes)
col4.metric("🦠 Archivos en cuarentena", archivos_cuarentena)

st.divider()

# -------------------------
# TABLA DE REPORTES
# -------------------------
st.subheader("📋 Últimos reportes del enjambre")
data = db.all()

if data:
    for item in data[-10:][::-1]:  # últimos 10
        st.write(f"**Abeja:** {item['agent']} | **Archivo:** {item.get('file', 'N/A')} | 🕒 {item.get('datetime', '')}")
else:
    st.info("Aún no hay reportes registrados.")

st.divider()

# -------------------------
# GRÁFICO DE ACTIVIDAD
# -------------------------
st.subheader("📊 Actividad del enjambre")

# Contar reportes por agente
agents = {}
for r in data:
    a = r['agent']
    agents[a] = agents.get(a, 0) + 1

if agents:
    fig, ax = plt.subplots()
    ax.bar(agents.keys(), agents.values())
    plt.xticks(rotation=45)
    st.pyplot(fig)
else:
    st.info("No hay datos para graficar aún.")

st.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
