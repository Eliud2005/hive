import tkinter as tk
from tkinter import ttk
from datetime import datetime
from PIL import Image, ImageTk

# ================================
#      CONFIGURACIÓN GENERAL
# ================================
PRIMARY = "#FFC107"        # Amarillo abeja
PRIMARY_DARK = "#FFB300"
BACKGROUND = "#1E1E1E"     # Gris muy oscuro
TEXT_COLOR = "#FFFFFF"


# ================================
#           VENTANA
# ================================
window = tk.Tk()
window.title("BeeShield – Centro de Protección")
window.geometry("720x500")
window.config(bg=BACKGROUND)
window.resizable(False, False)

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 11), padding=6)


# ================================
#         LOGO / ENCABEZADO
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

title_label = tk.Label(
    header_frame,
    text="BeeShield – Antivirus Inteligente",
    bg=BACKGROUND,
    fg=PRIMARY,
    font=("Segoe UI", 24, "bold")
)
title_label.pack(side="left")


# ================================
#         ESTADO DEL SISTEMA
# ================================
status_frame = tk.Frame(window, bg=BACKGROUND)
status_frame.pack(pady=10)

estado_label = tk.Label(
    status_frame,
    text="● Protección Activa",
    font=("Segoe UI", 18, "bold"),
    bg=BACKGROUND,
    fg="#4CAF50"    # Verde activo
)
estado_label.pack()


# ================================
#              LOGS
# ================================
logs_label = tk.Label(window, text="Actividad reciente", bg=BACKGROUND, fg=PRIMARY, font=("Segoe UI", 13))
logs_label.pack()

logs_frame = tk.Frame(window, bg=BACKGROUND)
logs_frame.pack()

logs = tk.Text(
    logs_frame,
    height=12,
    width=80,
    bg="#121212",
    fg="#E0E0E0",
    font=("Consolas", 10),
    bd=2,
    relief="flat"
)
logs.pack(pady=5)


def agregar_log(msg):
    tiempo = datetime.now().strftime("%H:%M:%S")
    logs.insert(tk.END, f"[{tiempo}] {msg}\n")
    logs.see(tk.END)


# ================================
#           BOTONES
# ================================
buttons_frame = tk.Frame(window, bg=BACKGROUND)
buttons_frame.pack(pady=20)

def activar():
    estado_label.config(text="● Protección Activa", fg="#4CAF50")
    agregar_log("Protección activada por el usuario.")

def desactivar():
    estado_label.config(text="● Protección Desactivada", fg="#F44336")
    agregar_log("Protección desactivada por el usuario.")

btn_on = ttk.Button(buttons_frame, text="Activar protección", command=activar)
btn_on.grid(row=0, column=0, padx=10)

btn_off = ttk.Button(buttons_frame, text="Desactivar protección", command=desactivar)
btn_off.grid(row=0, column=1, padx=10)


# ================================
#       LOG INICIAL
# ================================
agregar_log("BeeShield iniciado. Las abejas obreras están vigilando el sistema.")


window.mainloop()
