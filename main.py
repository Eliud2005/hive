# Copyright (c) 2025 Eliud García. Todos los derechos reservados.
from watchdog.observers import Observer
from agents.agent import Agent
from queen.queen import Queen
import time
from rich.console import Console
from rich.table import Table


def mostrar_menu():
    print("\n[1] Generar reporte PDF")
    print("[2] Salir")
    return input("Elige una opción: ")
def generar_reporte(db, filename="reporte.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        for item in db.all():
            f.write(f"{item.get('datetime', '')} - {item['agent']} - {item['file']}\n")
    print(f"Reporte guardado en {filename}")

from fpdf import FPDF
# ...existing code...

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
    table = Table(title="Miel de la Colmena")
    table.add_column("Agente")
    table.add_column("Archivo detectado")
    table.add_column("Fecha y hora")
    for item in db.all():
        table.add_row(item['agent'], item['file'],item.get('datetime', ''))
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
        time.sleep(1)  # Checa cada segundo
        current_count = len(queen.hive)
        if current_count != last_count:
            mostrar_miel(queen.hive)
            last_count = current_count
        
          # Mostrar menú después de la tabla
        opcion = mostrar_menu()
        if opcion == "1":
            generar_reporte_pdf(queen.hive)
        elif opcion == "2":
            break
except KeyboardInterrupt:
    observer.stop()
observer.join()
# Al final de tu main.py, antes de observer.join()
generar_reporte(queen.hive)