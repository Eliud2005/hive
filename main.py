import threading
import os
import glob
import time
import sys
from watchdog.observers import Observer
from agents.abeja_archivos import AbejaArchivos
from agents.abeja_procesos import AbejaProcesos
from agents.abeja_red import AbejaRed
from queen.queen import Queen
from agents.agent import move_to_quarantine
from interface import run_interface

# ---------------- Carpetas ----------------
TEST_FOLDER = "tests/files"
QUARANTINE_FOLDER = "quarantine"
os.makedirs(TEST_FOLDER, exist_ok=True)
os.makedirs(QUARANTINE_FOLDER, exist_ok=True)
SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.js', '.vbs', '.scr', '.cmd']

# ---------------- Queen ----------------
queen = Queen()

# ---------------- Agentes ----------------
agent1 = AbejaArchivos(queen, signature="sig1", data={})
agent2 = AbejaProcesos(queen)
agent3 = AbejaRed(queen)

observer = Observer()
observer.schedule(agent1, path=TEST_FOLDER, recursive=True)
observer.schedule(agent2, path=TEST_FOLDER, recursive=True)
observer.schedule(agent3, path=TEST_FOLDER, recursive=True)
observer.start()

# ---------------- Función escaneo manual ----------------
def escaneo_manual(path, queen, agent_name="EscaneoManual"):
    temp_agent = queen.create_agent(agent_name)
    for filepath in glob.glob(f"{path}/**", recursive=True):
        if os.path.isfile(filepath):
            _, ext = os.path.splitext(filepath)
            if ext.lower() in SUSPICIOUS_EXTENSIONS:
                queen.report(agent_name, filepath, temp_agent.signature, temp_agent.data)
                move_to_quarantine(filepath)

# ---------------- Consola opcional ----------------
def consola():
    while True:
        time.sleep(1)
        comando = input("Escribe 'menu' o ENTER: ").strip().lower()
        if comando == "menu":
            print("Opciones: 1. Escaneo manual | 2. Generar PDF | 0. Salir")
            opcion = input("Elige opción: ").strip()
            if opcion == "1":
                escaneo_manual(TEST_FOLDER, queen)
            elif opcion == "2":
                from rich.console import Console
                console = Console()
                console.print("Reporte generado en Desktop")
            elif opcion == "0":
                observer.stop()
                observer.join()
                os._exit(0)

# ---------------- Hilo consola ----------------
threading.Thread(target=consola, daemon=True).start()

# ---------------- Ejecutar GUI ----------------
try:
    run_interface(queen)
finally:
    observer.stop()
    observer.join()
    sys.exit()
