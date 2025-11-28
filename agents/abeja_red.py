from agents.agent import Agent
import psutil, time, threading, os, joblib
from cryptography.hazmat.primitives import hashes, serialization
import ipaddress

KEY_PATH = "data/keys/abeja_red_private.pem"
MODEL_PATH = "data/abeja3_model.pkl"  # Modelo de IA para red

# ---------------- IPs seguras (no interrumpir)
TRUSTED_IPS = {
    "127.0.0.1",        # loopback
    "0.0.0.0",          # cualquier
    "8.8.8.8", "8.8.4.4"  # DNS públicos (ejemplo)
}
# Rango local
LOCAL_NETWORKS = ["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]

def is_trusted_ip(ip):
    if ip in TRUSTED_IPS:
        return True
    for net in LOCAL_NETWORKS:
        if ipaddress.ip_address(ip) in ipaddress.ip_network(net):
            return True
    return False


class AbejaRed(Agent):
    CHECK_INTERVAL = 5  # segundos

    def __init__(self, queen, signature=None, data=None):
        super().__init__("AbejaRed", queen, signature, data)
        self.connections_previas = set()
        self.private_key = None

        # ---------------- Cargar clave privada ----------------
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
                print("[DSA] Clave privada de AbejaRed cargada y pública registrada.")
            except Exception as e:
                print("[DSA] Error al cargar clave privada:", e)
        else:
            print("[DSA] No se encontró clave privada:", KEY_PATH)

        # ---------------- Cargar modelo de IA ----------------
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
            print("[IA] Modelo de red cargado desde abeja3_model.pkl.")
        else:
            self.model = None
            print("[IA] No se encontró el modelo:", MODEL_PATH)

    def _sign(self, message_bytes):
        if not self.private_key:
            return None
        return self.private_key.sign(message_bytes, hashes.SHA256())

    def _extract_features(self, conn):
        try:
            port = conn.raddr.port if conn.raddr else 0
            established = 1 if conn.status == "ESTABLISHED" else 0
            return [port, established]
        except Exception:
            return [0, 0]

    def scan_connections(self):
        conexiones_actuales = set()
        for conn in psutil.net_connections():
            if conn.status == "ESTABLISHED" and conn.raddr:
                destino = conn.raddr.ip

                # Filtrar IPs confiables
                if is_trusted_ip(destino):
                    continue

                conexiones_actuales.add(destino)
                nuevo = destino not in self.connections_previas

                sospechoso = False
                if nuevo and self.model:
                    features = self._extract_features(conn)
                    try:
                        pred = self.model.predict([features])[0]
                        sospechoso = pred == 1
                    except Exception as e:
                        print(f"[IA] Error al predecir conexión {destino}: {e}")

                if nuevo and sospechoso:
                    print(f"[AbejaRed] Nueva conexión sospechosa: {destino}")
                    timestamp = str(int(time.time()))
                    message = f"{destino}|{timestamp}".encode("utf-8")
                    signature = self._sign(message)
                    self.queen.report_connection(self.name, destino, signature, self.data, signed_message=message)

        self.connections_previas = conexiones_actuales

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while True:
            self.scan_connections()
            time.sleep(self.CHECK_INTERVAL)
