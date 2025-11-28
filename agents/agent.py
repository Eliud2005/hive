# agents/agent.py
from watchdog.events import FileSystemEventHandler
import os
import shutil
import threading
import time

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
    DEBOUNCE_INTERVAL = 0.5  # segundos

    def __init__(self, name, queen, signature=None, data=None, private_key=None):
        super().__init__()
        self.name = name
        self.queen = queen
        self.signature = signature
        self.data = data
        self.private_key = private_key
        self._recent_events = {}  # archivo → timestamp

    def _should_process(self, filepath):
        now = time.time()
        last = self._recent_events.get(filepath, 0)
        if now - last < self.DEBOUNCE_INTERVAL:
            return False
        self._recent_events[filepath] = now
        return True

    def _evaluate_risk(self, filepath):
        """
        Método que puede sobreescribirse en agentes con IA.
        Retorna un valor entre 0 y 1 (riesgo).
        Por defecto, detección simple por extensión.
        """
        _, ext = os.path.splitext(filepath)
        return 1.0 if ext.lower() in SUSPICIOUS_EXTENSIONS else 0.0

    def _sign(self, message_bytes):
        if not self.private_key:
            return None
        from cryptography.hazmat.primitives import hashes
        return self.private_key.sign(message_bytes, hashes.SHA256())

    def _process_file(self, filepath):
        riesgo = self._evaluate_risk(filepath)
        if riesgo > 0.85:
            move_to_quarantine(filepath)
        timestamp = str(int(time.time()))
        message = f"{filepath}|{timestamp}".encode("utf-8")
        signature = self._sign(message)
        self.queen.report(self.name, filepath, signature, self.data, signed_message=message)

    def on_created(self, event):
        if event.is_directory or not self._should_process(event.src_path):
            return
        self._process_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory or not self._should_process(event.src_path):
            return
        self._process_file(event.src_path)
