# Copyright (c) 2025 Eliud García. Todos los derechos reservados.
from watchdog.observers import Observer
from agents.agent import Agent
from agents.agent import move_to_quarantine
from queen.queen import Queen
import time
from rich.console import Console
from rich.table import Table
import sys
from fpdf import FPDF
import glob
import os
SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.js', '.vbs', '.scr', '.cmd']
def mostrar_menu():
    console = Console()
    console.print("\n[bold blue][1][/bold blue] [yellow]Escaneo manual[/yellow]")
    console.print("[bold blue][2][/bold blue] [green]Generar reporte PDF[/green]")
    console.print("[bold blue][0][/bold blue] [red]Salir[/red]")
    return input("Elige una opción: ")

def escaneo_manual(path, queen, agent_name="EscaneoManual"):
    for filepath in glob.glob(f"{path}/**", recursive=True):
        if os.path.isfile(filepath):
            _, ext = os.path.splitext(filepath)
            if ext.lower() in SUSPICIOUS_EXTENSIONS:
                print(f"[ESCANEO] Archivo sospechoso: {filepath}")
                move_to_quarantine(filepath)  # Mueve a cuarentena
            queen.report(agent_name, filepath)
    print("[ESCANEO] Escaneo manual finalizado.")


def generar_reporte_pdf(db, filename="reporte.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte de la Colmena", ln=True, align="C")
    pdf.ln(10)
    for item in db.all():
        linea = f"{item.get('datetime', '')} - {item['agent']} - {item['file']}"
        pdf.cell(0, 10, txt=linea, ln=True)
    pdf.output(filename)
    print(f"Reporte PDF guardado en {filename}")



def mostrar_miel(db):
    console = Console()
    table = Table(title="[bold yellow]Miel de la Colmena[/bold yellow]")
    table.add_column("Agente", style="cyan", justify="center")
    table.add_column("Archivo detectado", style="magenta")
    table.add_column("Fecha y hora", style="green")
    for item in db.all():
        table.add_row(item['agent'], item['file'], item.get('datetime', ''))
    console.print(table)

queen = Queen()
agent1 = Agent("Abeja1", queen)
agent2 = Agent("Abeja2", queen)
agent3 = Agent("Abeja3", queen)

observer = Observer()
observer.schedule(agent1, path="tests/files", recursive=True)
observer.schedule(agent2, path="tests/files", recursive=True)
observer.schedule(agent3,path="tests/files",recursive=True)
observer.start()

last_count = 0  # Guarda el número de registros previos



# Mostrar la tabla una vez al inicio
mostrar_miel(queen.hive)


try:
    while True:
        import time
        time.sleep(1)
        current_count = len(queen.hive)
        if current_count != last_count:
            mostrar_miel(queen.hive)
            last_count = current_count

        comando = input("Escribe 'menu' para ver opciones o ENTER para continuar: ").strip().lower()
        if comando == "menu":
            opcion = mostrar_menu()
            if opcion == "1":
                escaneo_manual("tests/files", queen)
            elif opcion == "2":
                generar_reporte_pdf(queen.hive)
            elif opcion == "0":
                observer.stop()
                observer.join()
                sys.exit()
except KeyboardInterrupt:
    observer.stop()
observer.join()