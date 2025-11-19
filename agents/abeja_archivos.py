# agents/abeja_archivos.py
from watchdog.events import FileSystemEventHandler
from agents.agent import Agent, move_to_quarantine
import os, joblib

SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.js', '.vbs', '.scr', '.cmd']
MODEL_PATH = os.path.abspath("data/abeja2_model.pk1")  # Asegúrate de que tu modelo está aquí

class AbejaArchivos(Agent, FileSystemEventHandler):
    def __init__(self, queen, signature=None, data=None):
        super().__init__("AbejaArchivos", queen, signature, data)

        # Cargar modelo de IA
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
            print("[IA] Modelo de archivos cargado.")
        else:
            self.model = None
            print("[IA] No se encontró modelo:", MODEL_PATH)

    # ---------------- EventHandler de Watchdog ----------------
    def on_created(self, event):
        if not event.is_directory:
            self._procesar(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._procesar(event.src_path)

    # ---------------- Procesar archivo ----------------
    def _procesar(self, filepath):
        _, ext = os.path.splitext(filepath)
        riesgo = 0

        if self.model and os.path.isfile(filepath):
            try:
                # Extraer características para IA: tamaño, extensión sospechosa
                mem = os.path.getsize(filepath) / 1024  # KB
                name_flag = 1 if any(x in filepath.lower() for x in ["malware", "virus", "badfile"]) else 0
                ext_flag = 1 if ext.lower() in SUSPICIOUS_EXTENSIONS else 0
                features = [[mem, name_flag, ext_flag]]
                prob = self.model.predict_proba(features)[0][1]  # Probabilidad de ser malicioso
                riesgo = round(prob*100, 2)  # porcentaje
            except Exception as e:
                print(f"[IA] Error al predecir {filepath}: {e}")

        # Si extensión sospechosa o IA dice riesgo >50%, mover a cuarentena
        if ext.lower() in SUSPICIOUS_EXTENSIONS or riesgo >= 50:
            move_to_quarantine(filepath)

        # Guardar el riesgo dentro de data para que Queen lo acepte
        self.queen.report(self.name, filepath, self.signature, {**self.data, "riesgo": riesgo})
        print(f"[AbejaArchivos] {filepath} -> Riesgo IA: {riesgo}%")
