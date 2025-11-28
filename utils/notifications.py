# utils/notifications.py

from rich.console import Console
console = Console()

def notify(message, gui_callback=None):
    # Consola
    try:
        console.print(f"[bold yellow]{message}[/bold yellow]")
    except:
        print(message)

    # Interfaz
    if gui_callback:
        gui_callback(message)
