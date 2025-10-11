# Copyright (c) 2025 Eliud García. Todos los derechos reservados.
import os
import glob
import sys
import time
from watchdog.observers import Observer
from plyer import notification
from rich.console import Console
from rich.table import Table
from fpdf import FPDF
from agents.agent import Agent, move_to_quarantine
from queen.queen import Queen

# Extensiones sospechosas
SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.js', '.vbs', '.scr', '.cmd']

# ---------------- Notificaciones ----------------
def notificar(titulo, mensaje):
    notification.notify(
        title=titulo,
        message=mensaje,
        timeout=5
    )

# ---------------- Menú de opciones ----------------
def mostrar_menu():
    console = Console()
    console.print("\n[bold blue][1][/bold blue] [yellow]Escaneo manual[/yellow]")
    console.print("[bold blue][2][/bold blue] [green]Generar reporte PDF[/green]")
    console.print("[bold blue][0][/bold blue] [red]Salir[/red]")
    return input("Elige una opción: ")

# ---------------- Escaneo manual ----------------
def escaneo_manual(path, queen, agent_name="EscaneoManual"):
    # Crear un agente temporal solo para este escaneo
    temp_agent = queen.create_agent(agent_name)
    
    for filepath in glob.glob(f"{path}/**", recursive=True):
        if os.path.isfile(filepath):
            _, ext = os.path.splitext(filepath)
            if ext.lower() in SUSPICIOUS_EXTENSIONS:
                print(f"[ESCANEO] Archivo sospechoso: {filepath}")
                move_to_quarantine(filepath)
            
            # Usar la firma y datos del agente
            queen.report(agent_name, filepath, temp_agent.signature, temp_agent.data)
    print("[ESCANEO] Escaneo manual finalizado.")


# ---------------- Generar reporte PDF ----------------
def generar_reporte_pdf(db, filename=None, logo_path=None):
    if filename is None:
        # Guardar en el escritorio por defecto
        filename = os.path.join(os.path.expanduser("~"), "Desktop", "Hive_Report.pdf")
    
    pdf = FPDF()
    pdf.add_page()

    # 🔹 Logo si existe
    if logo_path and os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30)

    # 🔹 Encabezado
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(w=0, h=15, text="Reporte de la Colmena - BeeCode", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)

    # 🔹 Tabla encabezado
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(60, 10, "Archivo", border=1, align="C", fill=True)
    pdf.cell(80, 10, "Agentes", border=1, align="C", fill=True)
    pdf.cell(50, 10, "Fecha y hora", border=1, align="C", fill=True)
    pdf.ln()

    # 🔹 Filas
    pdf.set_font("Helvetica", "", 12)
    fill = False
    for item in db.all():
        pdf.set_fill_color(240, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(60, 10, item.get("file",""), border=1, fill=True)
        pdf.cell(80, 10, item.get("agent",""), border=1, fill=True)
        pdf.cell(50, 10, item.get("datetime",""), border=1, fill=True)
        pdf.ln()
        fill = not fill

    pdf.output(filename)
    print(f"[QUEEN] Reporte PDF generado: {filename}")

# ---------------- Mostrar tabla en consola ----------------
def mostrar_miel(db):
    console = Console()
    table = Table(title="[bold yellow]Miel de la Colmena[/bold yellow]")
    table.add_column("Agente", style="cyan", justify="center")
    table.add_column("Archivo detectado", style="magenta")
    table.add_column("Fecha y hora", style="green")
    
    # Solo mostrar registros con archivo
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
agent1 = queen.create_agent("Abeja1")
agent2 = queen.create_agent("Abeja2")
agent3 = queen.create_agent("Abeja3")

observer = Observer()
observer.schedule(agent1, path="tests/files", recursive=True)
observer.schedule(agent2, path="tests/files", recursive=True)
observer.schedule(agent3, path="tests/files", recursive=True)
observer.start()

last_count = 0  # Número de registros previos

# Mostrar la tabla al inicio
mostrar_miel(queen.hive)

# ---------------- Bucle principal ----------------
try:
    while True:
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
                generar_reporte_pdf(queen.hive, 
                                    filename=os.path.join(os.path.expanduser("~"), "Desktop", "Hive_Report.pdf"), 
                                    logo_path="public/assets/bee7.png")
            elif opcion == "0":
                observer.stop()
                observer.join()
                sys.exit()
except KeyboardInterrupt:
    observer.stop()
observer.join()
