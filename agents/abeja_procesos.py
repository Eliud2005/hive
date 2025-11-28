from agents.agent import Agent, move_to_quarantine
import psutil, time, threading, os, joblib
from cryptography.hazmat.primitives import hashes, serialization

KEY_PATH = os.path.abspath("data/keys/abeja_procesos_private.pem")
MODEL_PATH = os.path.abspath("data/abeja2_model.pkl")

# ---------------- Procesos críticos que nunca tocar ni reportar
TRUSTED_PROCESSES = {
    "System", "Registry", "csrss.exe", "wininit.exe", "explorer.exe",
    "svchost.exe", "lsass.exe", "services.exe", "taskhostw.exe",
    "spoolsv.exe", "antivirus.exe", "System Idle Process"
}
TRUSTED_PIDS = {0, 4}  # PID de procesos de sistema que nunca tocar

class AbejaProcesos(Agent):
    CHECK_INTERVAL = 3  # segundos

    def __init__(self, queen, signature=None, data=None):
        super().__init__("AbejaProcesos", queen, signature, data)
        self.private_key = None

        if os.path.exists(KEY_PATH):
            with open(KEY_PATH, "rb") as f:
                key_data = f.read()
            try:
                self.private_key = serialization.load_pem_private_key(key_data, password=None)
                pub_pem = self.private_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                self.queen.register_public_key(self.name, pub_pem)
                print("[DSA] Clave privada de AbejaProcesos cargada y pública registrada.")
            except Exception as e:
                print("[DSA] Error al cargar clave privada:", e)
        else:
            print("[DSA] No se encontró clave privada:", KEY_PATH)

        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print(f"[IA] Modelo de procesos cargado desde: {MODEL_PATH}")
            except Exception as e:
                self.model = None
                print(f"[IA] Error al cargar modelo: {e} — se usarán heurísticas simples.")
        else:
            self.model = None
            print(f"[IA] Modelo de procesos no encontrado en: {MODEL_PATH} — se usarán heurísticas simples.")

    def _sign(self, message_bytes):
        if not self.private_key:
            return None
        return self.private_key.sign(message_bytes, hashes.SHA256())

    def _extract_features(self, proc):
        try:
            mem_kb = proc.memory_info().rss / 1024
            cpu_percent = proc.cpu_percent(interval=0.1)
            return [mem_kb, cpu_percent]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return [0, 0]

    def scan_processes(self):
        for proc in psutil.process_iter():
            try:
                # Ignorar procesos críticos por nombre o PID
                if proc.name() in TRUSTED_PROCESSES or proc.pid in TRUSTED_PIDS:
                    continue

                features = self._extract_features(proc)
                sospechoso = False

                if self.model:
                    try:
                        pred = self.model.predict([features])[0]
                        sospechoso = pred == 1
                    except Exception as e:
                        print(f"[IA] Error al predecir proceso {proc.name()}: {e}")

                if sospechoso:
                    # Solo alertar, no terminar ni mover
                    print(f"[AbejaProcesos] Proceso sospechoso (alerta): {proc.name()} (PID {proc.pid})")

                    timestamp = str(int(time.time()))
                    message = f"{proc.pid}|{proc.name()}|{timestamp}".encode("utf-8")
                    signature = self._sign(message)
                    self.queen.report(self.name, f"Proceso-{proc.pid}", signature, self.data, signed_message=message)

            except Exception:
                continue

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while True:
            self.scan_processes()
            time.sleep(self.CHECK_INTERVAL)
