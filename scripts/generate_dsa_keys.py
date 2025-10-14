# scripts/generate_dsa_keys.py
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives import serialization
import os

OUT_DIR = "data/keys"
os.makedirs(OUT_DIR, exist_ok=True)

agents = ["abeja_archivos", "abeja_procesos", "abeja_red"]

for agent in agents:
    # Generar clave privada DSA
    private_key = dsa.generate_private_key(key_size=2048)
    
    # Guardar clave privada
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    priv_path = os.path.join(OUT_DIR, f"{agent}_private.pem")
    with open(priv_path, "wb") as f:
        f.write(priv_pem)
    
    # Guardar clave pública
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    pub_path = os.path.join(OUT_DIR, f"{agent}_public.pem")
    with open(pub_path, "wb") as f:
        f.write(pub_pem)
    
    print(f"[OK] Claves generadas para {agent}: {priv_path}, {pub_path}")

print(f"Todas las claves generadas en {OUT_DIR}")
