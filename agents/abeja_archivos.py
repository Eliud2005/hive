# agents/abeja_archivos.py
from watchdog.events import FileSystemEventHandler
from agents.agent import Agent, move_to_quarantine
import os, joblib

SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.js', '.vbs', '.scr', '.cmd']
MODEL_PATH = os.path.abspath("data/abeja2_model.pk1")  # Modelo entrenado

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
        riesgo_ia = 0

        # ---------------- IA: Probabilidad real ----------------
        if self.model and os.path.isfile(filepath):
            try:
                mem = os.path.getsize(filepath) / 1024  # KB
                name_flag = 1 if any(x in filepath.lower() for x in ["malware", "virus", "badfile"]) else 0
                ext_flag = 1 if ext.lower() in SUSPICIOUS_EXTENSIONS else 0

                features = [[mem, name_flag, ext_flag]]
                prob = self.model.predict_proba(features)[0][1]
                riesgo_ia = round(prob * 100, 2)

            except Exception as e:
                print(f"[IA] Error al predecir {filepath}: {e}")

        # ---------------- Riesgo base por extensión ----------------
        riesgo_extension = 60 if ext.lower() in SUSPICIOUS_EXTENSIONS else 0

        # ---------------- Riesgo final ----------------
        riesgo_final = max(riesgo_ia, riesgo_extension)

        # ===================================================
        #        🔥 NUEVO: ENVIAR RIESGO A LA INTERFAZ
        # ===================================================
        if hasattr(self.queen, "gui_notify_risk"):
            self.queen.gui_notify_risk(riesgo_final)

        # ===================================================
        #   🔥 NUEVO: LOG AUTOMÁTICO SI RIESGO ES SIGNIFICATIVO
        # ===================================================
        if riesgo_final >= 50:
            if hasattr(self.queen, "gui_notify"):
                self.queen.gui_notify(f"⚠ Riesgo IA ({riesgo_final}%) en {filepath}")

        # ---------------- Cuarentena ----------------
        if riesgo_final >= 50:
            move_to_quarantine(filepath)

        # ---------------- Reporte a Queen ----------------
        self.queen.report(
            self.name,
            filepath,
            self.signature,
            {**self.data, "riesgo": riesgo_final}
        )

        print(f"[AbejaArchivos] {filepath} -> Riesgo {riesgo_final}%")
