# main.py
# Copyright (c) 2025 Eliud García. Todos los derechos reservados.
import os
import glob
import sys
import time
from watchdog.observers import Observer
from plyer import notification
from rich.console import Console
from rich.table import Table
from queen.queen import Queen
from agents.agent import move_to_quarantine
from agents.abeja_archivos import AbejaArchivos
from agents.abeja_procesos import AbejaProcesos
from agents.abeja_red import AbejaRed

# ---------------- Carpetas necesarias ----------------
TEST_FOLDER = "tests/files"
QUARANTINE_FOLDER = "quarantine"

os.makedirs(TEST_FOLDER, exist_ok=True)
os.makedirs(QUARANTINE_FOLDER, exist_ok=True)

# ---------------- Extensiones sospechosas ----------------
SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.js', '.vbs', '.scr', '.cmd']

# ---------------- Notificaciones ----------------
def notificar(titulo, mensaje):
    notification.notify(title=titulo, message=mensaje, timeout=5)

# ---------------- Menú de opciones ----------------
def mostrar_menu():
    console = Console()
    console.print("\n[bold blue][1][/bold blue] [yellow]Escaneo manual[/yellow]")
    console.print("[bold blue][2][/bold blue] [green]Generar reporte PDF[/green]")
    console.print("[bold blue][0][/bold blue] [red]Salir[/red]")
    return input("Elige una opción: ").strip()

# ---------------- Escaneo manual ----------------
def escaneo_manual(path, queen, agent_name="EscaneoManual"):
    temp_agent = queen.create_agent(agent_name)
    for filepath in glob.glob(f"{path}/**", recursive=True):
        if os.path.isfile(filepath):
            _, ext = os.path.splitext(filepath)
            if ext.lower() in SUSPICIOUS_EXTENSIONS:
                print(f"[ESCANEO] Archivo sospechoso: {filepath}")
                move_to_quarantine(filepath)
            queen.report(agent_name, filepath, temp_agent.signature, temp_agent.data)
    print("[ESCANEO] Escaneo manual finalizado.")

# ---------------- Mostrar tabla en consola ----------------
def mostrar_miel(db):
    console = Console()
    table = Table(title="[bold yellow]Miel de la Colmena[/bold yellow]")
    table.add_column("Agente", style="cyan", justify="center")
    table.add_column("Archivo detectado", style="magenta")
    table.add_column("Fecha y hora", style="green")
    for item in db.all():
        if 'file' in item and item['file']:
            table.add_row(
                item.get('agent', ''),
                item.get('file', ''),
                item.get('datetime', '')
            )
    console.print(table)

# ---------------- Inicialización ----------------
queen = Queen()

# ---------------- Crear agentes ----------------
agent1 = AbejaArchivos(queen, signature="sig1", data={})
agent2 = AbejaProcesos(queen)
agent3 = AbejaRed(queen)

# ---------------- Observer ----------------
observer = Observer()
observer.schedule(agent1, path=TEST_FOLDER, recursive=True)
observer.schedule(agent2, path=TEST_FOLDER, recursive=True)
observer.schedule(agent3, path=TEST_FOLDER, recursive=True)
observer.start()

# Mostrar datos iniciales
last_count = 0
mostrar_miel(queen.hive)

# ---------------- Bucle principal ----------------
try:
    while True:
        time.sleep(1)
        # Actualizar tabla si hay cambios
        current_count = len(queen.hive)
        if current_count != last_count:
            mostrar_miel(queen.hive)
            last_count = current_count

        comando = input("Escribe 'menu' para opciones o ENTER para continuar: ").strip().lower()
        if comando == "menu":
            opcion = mostrar_menu()
            if opcion == "1":
                escaneo_manual(TEST_FOLDER, queen)
            elif opcion == "2":
                queen.generate_pdf_report(
                    filename=os.path.join(os.path.expanduser("~"), "Desktop", "Hive_Report.pdf"),
                    logo_path="public/assets/bee7.png"
                )
            elif opcion == "0":
                observer.stop()
                observer.join()
                sys.exit()
except KeyboardInterrupt:
    observer.stop()
observer.join()
