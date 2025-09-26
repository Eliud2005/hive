from watchdog.observers import Observer
from agents.agent import Agent
from queen.queen import Queen
import time
from rich.console import Console
from rich.table import Table

def mostrar_miel(db):
    console = Console()
    table = Table(title="Miel de la Colmena")
    table.add_column("Agente")
    table.add_column("Archivo detectado")
    for item in db.all():
        table.add_row(item['agent'], item['file'])
    console.print(table)

queen = Queen()
agent1 = Agent("Abeja1", queen)
agent2 = Agent("Abeja2", queen)

observer = Observer()
observer.schedule(agent1, path="tests/files", recursive=True)
observer.schedule(agent2, path="tests/files", recursive=True)
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
except KeyboardInterrupt:
    observer.stop()
observer.join()