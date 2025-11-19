# interface.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import os

# ================================
#      COLORES Y ESTILO
# ================================
PRIMARY = "#FFC107"
BACKGROUND = "#1E1E1E"
TEXT_COLOR = "#FFFFFF"

# ================================
#       VENTANA PRINCIPAL
# ================================
window = tk.Tk()
window.title("BeeShield – Centro de Protección")
window.geometry("900x600")
window.config(bg=BACKGROUND)
window.resizable(True, True)

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 11), padding=6)

# ================================
#         LOGO Y ENCABEZADO
# ================================
header_frame = tk.Frame(window, bg=BACKGROUND)
header_frame.pack(fill="x", pady=20)

try:
    logo_img = Image.open("logo.png").resize((110, 110), Image.LANCZOS)
    logo = ImageTk.PhotoImage(logo_img)
    logo_label = tk.Label(header_frame, image=logo, bg=BACKGROUND)
    logo_label.pack(side="left", padx=25)
except:
    logo_label = tk.Label(header_frame, text="🐝", bg=BACKGROUND, fg=PRIMARY, font=("Segoe UI", 60))
    logo_label.pack(side="left", padx=25)

title_label = tk.Label(header_frame, text="BeeShield – Antivirus Inteligente",
                       bg=BACKGROUND, fg=PRIMARY, font=("Segoe UI", 24, "bold"))
title_label.pack(side="left")

# ================================
#       ESTADO DEL SISTEMA
# ================================
status_frame = tk.Frame(window, bg=BACKGROUND)
status_frame.pack(pady=10)

estado_label = tk.Label(status_frame, text="● Protección Activa",
                        font=("Segoe UI", 18, "bold"), bg=BACKGROUND, fg="#4CAF50")
estado_label.pack()

# ================================
#       LOGS DE EVENTOS
# ================================
logs_label = tk.Label(window, text="Actividad reciente", bg=BACKGROUND, fg=PRIMARY, font=("Segoe UI", 13))
logs_label.pack()

logs_frame = tk.Frame(window, bg=BACKGROUND)
logs_frame.pack()

logs = tk.Text(logs_frame, height=12, width=100, bg="#121212", fg="#E0E0E0",
               font=("Consolas", 10), bd=2, relief="flat")
logs.pack(pady=5, padx=10)

def agregar_log(msg):
    tiempo = datetime.now().strftime("%H:%M:%S")
    logs.insert(tk.END, f"[{tiempo}] {msg}\n")
    logs.see(tk.END)

# ================================
#        BOTONES PRINCIPALES
# ================================
buttons_frame = tk.Frame(window, bg=BACKGROUND)
buttons_frame.pack(pady=20)

def activar():
    estado_label.config(text="● Protección Activa", fg="#4CAF50")
    agregar_log("Protección activada.")

def desactivar():
    estado_label.config(text="● Protección Desactivada", fg="#F44336")
    agregar_log("Protección desactivada.")

def generar_pdf():
    try:
        path_pdf = os.path.join(os.path.expanduser("~"), "Desktop", "Hive_Report.pdf")
        queen.generate_pdf_report(filename=path_pdf, logo_path="public/assets/bee7.png")
        messagebox.showinfo("PDF Generado", f"Reporte generado en: {path_pdf}")
        agregar_log("Reporte PDF generado en Desktop.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo generar el PDF: {e}")
        agregar_log(f"[ERROR] Falló la generación del PDF: {e}")

btn_on = ttk.Button(buttons_frame, text="Activar protección", command=activar)
btn_on.grid(row=0, column=0, padx=10)

btn_off = ttk.Button(buttons_frame, text="Desactivar protección", command=desactivar)
btn_off.grid(row=0, column=1, padx=10)

btn_pdf = ttk.Button(buttons_frame, text="Generar Reporte PDF", command=generar_pdf)
btn_pdf.grid(row=0, column=2, padx=10)

btn_scan = ttk.Button(buttons_frame, text="Escaneo Manual", command=lambda: queen.escaneo_manual())
btn_scan.grid(row=0, column=3, padx=10)

# ================================
#      GRÁFICA DE EVENTOS
# ================================
graph_frame = tk.Frame(window, bg=BACKGROUND)
graph_frame.pack(pady=10, fill="both", expand=True)

fig = Figure(figsize=(6,3), dpi=100)
ax = fig.add_subplot(111)
ax.set_title("Eventos por agente")
ax.set_xlabel("Agentes")
ax.set_ylabel("Número de eventos")
bar_canvas = FigureCanvasTkAgg(fig, master=graph_frame)
bar_canvas.get_tk_widget().pack(fill="both", expand=True)

def actualizar_grafica():
    agentes = {}
    for evento in queen.hive.all():
        agente = evento.get("agent", "Desconocido")
        agentes[agente] = agentes.get(agente, 0) + 1

    ax.clear()
    ax.bar(agentes.keys(), agentes.values(), color="#FFC107")
    ax.set_title("Eventos por agente")
    ax.set_xlabel("Agentes")
    ax.set_ylabel("Número de eventos")
    bar_canvas.draw()
    window.after(1000, actualizar_grafica)

# ================================
#   ACTUALIZAR LOGS AUTOMÁTICAMENTE
# ================================
def actualizar_logs():
    registros = queen.hive.all()
    if not hasattr(actualizar_logs, "last_count"):
        actualizar_logs.last_count = 0

    nuevos_eventos = registros[actualizar_logs.last_count:]
    for evento in nuevos_eventos:
        archivo = evento.get("file", "")
        agente = evento.get("agent", "")
        agregar_log(f"[{agente}] detectó cambio: {archivo}")

    actualizar_logs.last_count = len(registros)
    window.after(1000, actualizar_logs)

# ================================
#       FUNCION PRINCIPAL
# ================================
def run_interface(q, escaneo_manual_func):
    global queen
    queen = q
    queen.escaneo_manual = escaneo_manual_func  # asignar función de escaneo al objeto Queen

    actualizar_logs()
    actualizar_grafica()
    window.mainloop()
