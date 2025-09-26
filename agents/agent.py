# agents/agent.py
import os
from watchdog.events import FileSystemEventHandler

SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.js', '.vbs', '.scr', '.cmd']
class Agent(FileSystemEventHandler):
    def __init__(self, name, queen):
        super().__init__()
        self.name = name
        self.queen = queen
        self.last_modified = {}  # Guarda el último timestamp de cada archivo

    def on_modified(self, event):
        if not event.is_directory:
            _, ext = os.path.splitext(event.src_path)
            if ext.lower() in SUSPICIOUS_EXTENSIONS:
                print(f"[ALERTA] {self.name} detectó archivo sospechoso: {event.src_path}")
            print(f"{self.name} detectó cambio en {event.src_path}")
            self.queen.report(self.name, event.src_path)
