import tkinter as tk
from tkinter import ttk
from datetime import datetime
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

PRIMARY = "#FFC107"
BACKGROUND = "#1E1E1E"
TEXT_COLOR = "#FFFFFF"

class BeeGUI:
    def __init__(self, queen):
        self.queen = queen
        self.window = tk.Tk()
        self.window.title("BeeShield – Centro de Protección")
        self.window.geometry("900x600")
        self.window.config(bg=BACKGROUND)

        self.setup_header()
        self.setup_status()
        self.setup_logs()
        self.setup_stats()
        self.setup_buttons()

        # Actualización periódica
        self.update_gui()
        self.window.mainloop()

    def setup_header(self):
        frame = tk.Frame(self.window, bg=BACKGROUND)
        frame.pack(fill="x", pady=10)
        try:
            logo_img = Image.open("assets/logo.png").resize((80, 80))
            self.logo = ImageTk.PhotoImage(logo_img)
            tk.Label(frame, image=self.logo, bg=BACKGROUND).pack(side="left", padx=10)
        except:
            tk.Label(frame, text="🐝", bg=BACKGROUND, fg=PRIMARY, font=("Segoe UI", 40)).pack(side="left", padx=10)
        tk.Label(frame, text="BeeShield – Antivirus Inteligente", bg=BACKGROUND,
                 fg=PRIMARY, font=("Segoe UI", 24, "bold")).pack(side="left")

    def setup_status(self):
        self.status_label = tk.Label(self.window, text="● Protección Activa", font=("Segoe UI", 16, "bold"),
                                     bg=BACKGROUND, fg="#4CAF50")
        self.status_label.pack(pady=5)

    def setup_logs(self):
        tk.Label(self.window, text="Actividad reciente", bg=BACKGROUND, fg=PRIMARY, font=("Segoe UI", 12)).pack()
        self.logs = tk.Text(self.window, height=12, width=110, bg="#121212", fg="#E0E0E0", font=("Consolas", 10))
        self.logs.pack(pady=5)

    def setup_stats(self):
        tk.Label(self.window, text="Estadísticas de la colmena", bg=BACKGROUND, fg=PRIMARY, font=("Segoe UI", 12)).pack()
        self.fig, self.ax = plt.subplots(figsize=(8,3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)
        self.canvas.get_tk_widget().pack()
        self.event_count = 0

    def setup_buttons(self):
        frame = tk.Frame(self.window, bg=BACKGROUND)
        frame.pack(pady=10)
        ttk.Button(frame, text="Activar protección", command=self.activar).grid(row=0, column=0, padx=10)
        ttk.Button(frame, text="Desactivar protección", command=self.desactivar).grid(row=0, column=1, padx=10)
        ttk.Button(frame, text="Escaneo manual", command=self.escaneo_manual).grid(row=0, column=2, padx=10)

    def agregar_log(self, msg):
        tiempo = datetime.now().strftime("%H:%M:%S")
        self.logs.insert(tk.END, f"[{tiempo}] {msg}\n")
        self.logs.see(tk.END)

    def actualizar_stats(self):
        total_eventos = len(self.queen.hive)
        self.ax.clear()
        self.ax.bar(["Eventos"], [total_eventos], color=PRIMARY)
        self.ax.set_ylim(0, max(10, total_eventos+5))
        self.ax.set_ylabel("Cantidad")
        self.ax.set_title("Eventos detectados por la colmena")
        self.canvas.draw()

    def update_gui(self):
        # Actualiza logs y estadísticas
        for item in self.queen.hive.all():
            if 'reported' not in item:
                msg = f"Abeja '{item.get('agent')}' detectó: {item.get('file', 'evento')}"
                self.agregar_log(msg)
                item['reported'] = True
        self.actualizar_stats()
        self.window.after(1000, self.update_gui)  # Cada segundo

    def activar(self):
        self.status_label.config(text="● Protección Activa", fg="#4CAF50")
        self.agregar_log("Protección activada por el usuario.")

    def desactivar(self):
        self.status_label.config(text="● Protección Desactivada", fg="#F44336")
        self.agregar_log("Protección desactivada por el usuario.")

    def escaneo_manual(self):
        from main import escaneo_manual, TEST_FOLDER
        escaneo_manual(TEST_FOLDER, self.queen)
        self.agregar_log("Escaneo manual completado.")

def run_interface(queen):
    BeeGUI(queen)
