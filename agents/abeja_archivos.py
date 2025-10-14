# agents/abeja_archivos.py
from agents.agent import Agent, move_to_quarantine
import os, joblib, pefile, time
import numpy as np
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dsa

KEY_PATH = "data/keys/abeja_archivos_private.pem"
MODEL_PATH = "data/abeja1_model.pkl"

class AbejaArchivos(Agent):
    def __init__(self, queen, signature=None, data=None):
        super().__init__("AbejaArchivos", queen, signature, data)
        
        # Cargar modelo IA
        try:
            self.model = joblib.load(MODEL_PATH)
            print("[IA] Modelo de AbejaArchivos cargado.")
        except Exception as e:
            self.model = None
            print("[IA] No se encontró modelo, detección básica activada.", e)

        # Cargar clave privada DSA
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
                try:
                    self.queen.register_public_key(self.name, pub_pem)
                except Exception:
                    pass
                print("[DSA] Clave privada cargada y pública registrada en Queen.")
            except Exception as e:
                print("[DSA] Error cargando clave privada:", e)
        else:
            print("[DSA] No se encontró clave privada:", KEY_PATH)

    def _extract_features(self, filepath):
        try:
            pe = pefile.PE(filepath)
            entropia = np.mean([s.get_entropy() for s in pe.sections])
            return [os.path.getsize(filepath)/1024, len(pe.sections), entropia]
        except Exception:
            try:
                return [os.path.getsize(filepath)/1024, 0, 0]
            except:
                return [0,0,0]

    def _sign(self, message_bytes):
        if not self.private_key:
            return None
        return self.private_key.sign(message_bytes, hashes.SHA256())

    def on_created(self, event):
        if event.is_directory:
            return

        filepath = event.src_path
        _, ext = os.path.splitext(filepath)
        if ext.lower() not in ['.exe', '.dll', '.scr']:
            return

        features = self._extract_features(filepath)
        riesgo = self.model.predict_proba([features])[0][1] if self.model else 0.8 if features[0]>500 else 0.2
        print(f"[AbejaArchivos] Riesgo IA: {riesgo:.2f} en {filepath}")

        if riesgo > 0.85:
            move_to_quarantine(filepath)

        # Mensaje firmado
        timestamp = str(int(time.time()))
        message = f"{filepath}|{timestamp}".encode("utf-8")
        signature = self._sign(message)

        self.queen.report(self.name, filepath, signature, self.data, signed_message=message)
