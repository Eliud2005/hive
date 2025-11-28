# main.py
import os
import glob
import threading
from watchdog.observers import Observer
from queen.queen import Queen
from agents.agent import move_to_quarantine
from agents.abeja_archivos import AbejaArchivos
from agents.abeja_procesos import AbejaProcesos
from agents.abeja_red import AbejaRed
from interface import run_interface

# ---------------- Carpetas necesarias ----------------
TEST_FOLDER = "tests/files"
QUARANTINE_FOLDER = "quarantine"
os.makedirs(TEST_FOLDER, exist_ok=True)
os.makedirs(QUARANTINE_FOLDER, exist_ok=True)

# ---------------- Extensiones sospechosas ----------------
SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.js', '.vbs', '.scr', '.cmd']

# ---------------- Inicialización de Queen ----------------
queen = Queen()

# ---------------- Crear agentes ----------------
agent1 = AbejaArchivos(queen, signature="sig1", data={})
agent2 = AbejaProcesos(queen)
agent3 = AbejaRed(queen)

# ---------------- Iniciar loops internos de agentes ----------------
agent2.start()  # Procesos
agent3.start()  # Red

# ---------------- Observer para AbejaArchivos ----------------
observer = Observer()
observer.schedule(agent1, path=TEST_FOLDER, recursive=True)
observer_thread = threading.Thread(target=observer.start, daemon=True)
observer_thread.start()

# ---------------- Escaneo manual (para el botón en GUI) ----------------
def escaneo_manual(gui_callback=None):
    temp_agent = queen.create_agent("EscaneoManual")

    if gui_callback:
        gui_callback("Inicio de escaneo manual...")

    for filepath in glob.glob(f"{TEST_FOLDER}/**", recursive=True):
        if os.path.isfile(filepath):
            _, ext = os.path.splitext(filepath)

            # mover archivos sospechosos
            if ext.lower() in SUSPICIOUS_EXTENSIONS:
                move_to_quarantine(filepath)
                msg = f"Archivo movido a cuarentena: {filepath}"
                print(msg)
                if gui_callback:
                    gui_callback(msg)

            # reportar al hive
            queen.report(
                "EscaneoManual",
                filepath,
                signature=temp_agent.signature,
                data=temp_agent.data
            )

            msg = f"[EscaneoManual] Analizado: {filepath}"
            print(msg)
            if gui_callback:
                gui_callback(msg)

    fin = "Escaneo manual completado."
    print(fin)
    if gui_callback:
        gui_callback(fin)

# ---------------- Ejecutar interfaz ----------------
try:
    run_interface(queen, escaneo_manual)
finally:
    observer.stop()
    observer.join()
