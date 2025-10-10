from watchdog.events import FileSystemEventHandler
import os
import shutil

SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.js', '.vbs', '.scr', '.cmd']
QUARANTINE_FOLDER = "quarantine"

def move_to_quarantine(filepath):
    if not os.path.exists(filepath):
        print(f"[CUARENTENA] El archivo no existe: {filepath}")
        return
    if not os.path.exists(QUARANTINE_FOLDER):
        os.makedirs(QUARANTINE_FOLDER)
    filename = os.path.basename(filepath)
    destino = os.path.join(QUARANTINE_FOLDER, filename)
    shutil.move(filepath, destino)
    print(f"[CUARENTENA] Archivo movido a: {destino}")

class Agent(FileSystemEventHandler):
    def __init__(self, name, queen, signature):
        super().__init__()
        self.name = name
        self.queen = queen
        self.signature = signature

    def on_created(self, event):
        if not event.is_directory:
            _, ext = os.path.splitext(event.src_path)
            if ext.lower() in SUSPICIOUS_EXTENSIONS:
                print(f"[ALERTA] {self.name} detectó archivo sospechoso creado: {event.src_path}")
                move_to_quarantine(event.src_path)
            print(f"{self.name} detectó creación de {event.src_path}")
            self.queen.report(self.name, event.src_path, self.signature)

    def on_modified(self, event):
        if not event.is_directory:
            _, ext = os.path.splitext(event.src_path)
            if ext.lower() in SUSPICIOUS_EXTENSIONS:
                print(f"[ALERTA] {self.name} detectó archivo sospechoso: {event.src_path}")
                move_to_quarantine(event.src_path)
            print(f"{self.name} detectó cambio en {event.src_path}")
            self.queen.report(self.name, event.src_path, self.signature)
