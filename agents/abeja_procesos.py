# agents/abeja_procesos.py
from agents.agent import Agent, move_to_quarantine
import psutil, time, threading, os, joblib
from cryptography.hazmat.primitives import hashes, serialization

KEY_PATH = os.path.abspath("data/keys/abeja_procesos_private.pem")
MODEL_PATH = os.path.abspath("data/abeja2_model.pk1")


class AbejaProcesos(Agent):
    CHECK_INTERVAL = 3  # segundos

    def __init__(self, queen, signature=None, data=None):
        super().__init__("AbejaProcesos", queen, signature, data)

        # ---------------- Cargar clave privada ----------------
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

        # ---------------- Cargar modelo de IA ----------------
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
            print("[IA] Modelo de procesos cargado desde abeja2_model.pk1.")
        else:
            self.model = None
            print("[IA] No se encontró el modelo:", MODEL_PATH)

    # ---------------- Firma DSA ----------------
    def _sign(self, message_bytes):
        if not self.private_key:
            return None
        return self.private_key.sign(message_bytes, hashes.SHA256())

    # ---------------- Extraer características para IA ----------------
    def _extract_features(self, proc):
        try:
            mem_kb = proc.memory_info().rss / 1024
            cpu_percent = proc.cpu_percent(interval=0.1)
            name_flag = 1 if any(x in proc.name().lower() for x in ["malware", "virus", "badprocess"]) else 0
            return [mem_kb, cpu_percent, name_flag]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return [0, 0, 0]

    # ---------------- Escaneo de procesos ----------------
    def scan_processes(self):
        for proc in psutil.process_iter():
            features = self._extract_features(proc)
            sospechoso = False

            # Evaluar con IA si existe el modelo
            if self.model:
                try:
                    pred = self.model.predict([features])[0]
                    sospechoso = pred == 1
                except Exception as e:
                    print(f"[IA] Error al predecir proceso {proc.name()}: {e}")

            if sospechoso:
                print(f"[AbejaProcesos] Proceso sospechoso: {proc.name()} (PID {proc.pid})")
                try:
                    proc.terminate()
                    move_to_quarantine(f"Proceso-{proc.pid}")
                except Exception as e:
                    print(f"[AbejaProcesos] No se pudo detener proceso: {e}")

                timestamp = str(int(time.time()))
                message = f"{proc.pid}|{proc.name()}|{timestamp}".encode("utf-8")
                signature = self._sign(message)
                self.queen.report(self.name, f"Proceso-{proc.pid}", signature, self.data, signed_message=message)

    # ---------------- Loop de monitoreo ----------------
    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while True:
            self.scan_processes()
            time.sleep(self.CHECK_INTERVAL)
