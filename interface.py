# ================================================
#                  BeeShield UI
#        Interfaz CyberDark para Antivirus
# ================================================

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import os

# ================================
#      COLORES Y ESTILOS
# ================================
DARK_BG = "#0A0A0A"
CARD_BG = "#111111"
ACCENT = "#00FFC6"
TEXT = "#EAEAEA"

# Paleta más suave / agradable para la gráfica
PLOT_BG = "#0F1724"      # Figura exterior (ligeramente azulado)
PLOT_FACE = "#0B1220"    # Fondo dentro del eje (oscuro pero suave)
PLOT_TEXT = "#E6EEF6"    # Texto en la gráfica (suave, alto contraste)
PLOT_COLORS = [
    "#5BD1FF",  # agua
    "#A0E7B8",  # verde suave
    "#FFD27F",  # amarillo cálido
    "#FF9AA2",  # rosado suave
    "#C7B7FF",  # lila suave
]

# ================================
#      VENTANA PRINCIPAL
# ================================
window = tk.Tk()
window.title("BeeShield – CyberDark Antivirus")
window.geometry("1000x700")
window.config(bg=DARK_BG)
window.resizable(True, True)

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 11), padding=10, background=ACCENT)
style.map("TButton", background=[("active", "#00DDAA")])

# ================================
#          ENCABEZADO
# ================================
header = tk.Frame(window, bg=DARK_BG)
header.pack(fill="x", pady=10)

try:
    logo_img = Image.open("logo.png").resize((80, 80))
    logo = ImageTk.PhotoImage(logo_img)
    logo_lbl = tk.Label(header, image=logo, bg=DARK_BG)
    logo_lbl.pack(side="left", padx=15)
except:
    logo_lbl = tk.Label(header, text="🛡️", font=("Segoe UI", 50), bg=DARK_BG, fg=ACCENT)
    logo_lbl.pack(side="left", padx=15)

title = tk.Label(header, text="BeeShield CyberDark",
                 font=("Segoe UI", 28, "bold"), fg=ACCENT, bg=DARK_BG)
title.pack(side="left", padx=6, pady=6)

time_label = tk.Label(header, text="", font=("Segoe UI", 12),
                      fg="#888", bg=DARK_BG)
time_label.pack(side="right", padx=12)

def update_time():
    now = datetime.now().strftime("%H:%M:%S")
    time_label.config(text=now)
    window.after(1000, update_time)

update_time()

# ================================
#       ESTADO DEL SISTEMA
# ================================
state_frame = tk.Frame(window, bg=CARD_BG)
state_frame.pack(pady=10, fill="x", padx=20)

state_label = tk.Label(state_frame, text="● Protección Activa",
                       font=("Segoe UI", 20, "bold"), fg="#00FF88", bg=CARD_BG)
state_label.pack(pady=10)

# ================================
#       BOTONES PRINCIPALES
# ================================
btn_frame = tk.Frame(window, bg=DARK_BG)
btn_frame.pack(pady=10)

def activar():
    state_label.config(text="● Protección Activa", fg="#00FF88")
    agregar_log("Protección activada.")

def desactivar():
    state_label.config(text="● Protección Desactivada", fg="#FF4444")
    agregar_log("Protección desactivada.")

def generar_pdf():
    try:
        path_pdf = os.path.join(os.path.expanduser("~"), "Desktop", "Hive_Report.pdf")
        queen.generate_pdf_report(filename=path_pdf, logo_path="public/assets/bee7.png")
        messagebox.showinfo("PDF Generado", f"Reporte creado en Desktop.")
        agregar_log("PDF generado exitosamente.")
    except Exception as e:
        messagebox.showerror("Error PDF", str(e))
        agregar_log(f"[ERROR] PDF: {e}")

ttk.Button(btn_frame, text="Activar", command=activar).grid(row=0, column=0, padx=10)
ttk.Button(btn_frame, text="Desactivar", command=desactivar).grid(row=0, column=1, padx=10)
ttk.Button(btn_frame, text="Reporte PDF", command=generar_pdf).grid(row=0, column=2, padx=10)
ttk.Button(btn_frame, text="Escaneo Manual", command=lambda: queen.escaneo_manual()).grid(row=0, column=3, padx=10)

# ================================
#   FILTROS / VISIBILIDAD DE AGENTES
# ================================
# NOTE: Removed checkboxes — abeja1/2/3 are excluded permanently from the chart.

# ================================
#             LOGS
# ================================
logs_lbl = tk.Label(window, text="Actividad Reciente", fg=ACCENT,
                    bg=DARK_BG, font=("Segoe UI", 14))
logs_lbl.pack(anchor="w", padx=20)

logs = tk.Text(window, height=12, width=110, bg="#090909",
               fg="#29B99C", font=("Consolas", 10), bd=0)
logs.pack(padx=20, pady=5)

def agregar_log(msg):
    tiempo = datetime.now().strftime("%H:%M:%S")
    logs.insert(tk.END, f"[{tiempo}] {msg}\n")
    logs.see(tk.END)

# ================================
#         GRAFICADOR
# ================================
graph_frame = tk.Frame(window, bg=DARK_BG)
graph_frame.pack(fill="both", expand=True, padx=20, pady=10)

fig = Figure(figsize=(5, 3), dpi=100, facecolor=PLOT_BG)
ax = fig.add_subplot(111)
ax.set_facecolor(PLOT_FACE)
ax.set_title("Eventos por Agente", color=PLOT_TEXT)
ax.tick_params(colors=PLOT_TEXT)
# estilizar ejes para que sigan la paleta suave
for spine in ax.spines.values():
    spine.set_color("#243142")
ax.xaxis.label.set_color(PLOT_TEXT)
ax.yaxis.label.set_color(PLOT_TEXT)

canvas = FigureCanvasTkAgg(fig, master=graph_frame)
canvas.get_tk_widget().pack(fill="both", expand=True)

def actualizar_grafica():
    agentes = {}

    for evento in queen.hive.all():
        ag = evento.get("agent", "Desconocido")
        agentes[ag] = agentes.get(ag, 0) + 1

    ax.clear()
    # mantener el fondo y estilo después de limpiar
    ax.set_facecolor(PLOT_FACE)

    # Respect visibility toggles: skip abeja1/2/3 if user turned them off
    # Exclude the agent names abeja1/abeja2/abeja3 permanently
    excluded_agents = {"abeja1", "abeja2", "abeja3", "abeja4"}
    filtered = {k: v for k, v in agentes.items() if k.lower() not in excluded_agents}

    if not filtered:
        # If nothing to show, give a friendly empty-state message
        ax.text(0.5, 0.5, "No hay agentes seleccionados",
                horizontalalignment='center', verticalalignment='center',
                color="#7E98A7", fontsize=12, transform=ax.transAxes)
    else:
        # usar paleta suave, rotando colores si hay más barras que colores
        colors = [PLOT_COLORS[i % len(PLOT_COLORS)] for i in range(len(filtered))]
        ax.bar(list(filtered.keys()), list(filtered.values()), color=colors, edgecolor="#13202A")

    ax.set_title("Eventos por Agente", color=PLOT_TEXT)
    ax.tick_params(colors=PLOT_TEXT)
    for spine in ax.spines.values():
        spine.set_color("#243142")
    canvas.draw()

    window.after(1200, actualizar_grafica)

# ================================
#    ACTUALIZACIÓN DE LOGS
# ================================
def actualizar_logs():
    registros = queen.hive.all()

    if not hasattr(actualizar_logs, "last"):
        actualizar_logs.last = 0

    nuevos = registros[actualizar_logs.last:]

    for evento in nuevos:
        archivo = evento.get("file", "??")
        agente = evento.get("agent", "??")
        agregar_log(f"[{agente}] Detectó cambio en {archivo}")

    actualizar_logs.last = len(registros)
    window.after(1200, actualizar_logs)

# ================================
#       FUNCIÓN PRINCIPAL
# ================================
def run_interface(q, escaneo_manual_func):
    global queen
    queen = q
    queen.escaneo_manual = escaneo_manual_func

    actualizar_logs()
    actualizar_grafica()
    window.mainloop()
