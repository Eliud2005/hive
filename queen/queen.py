from tinydb import TinyDB, Query
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from agents.agent import Agent  # Importa la clase Agent

class Queen:
    def __init__(self):
        self.hive = TinyDB('hive.json')
        self.query = Query()
        # Generamos clave privada y pública DSA
        self.private_key = dsa.generate_private_key(key_size=2048)
        self.public_key = self.private_key.public_key()

    def _generate_signature(self, name):
        # Genera datos a firmar
        data = f"{name}-{datetime.now().timestamp()}".encode()
        # Firma DSA real
        signature = self.private_key.sign(data, hashes.SHA256())
        return data, signature

    def create_agent(self, name):
        data, signature = self._generate_signature(name)
        # Guarda la firma y datos en la base
        self.hive.insert({
            'agent': name,
            'data': data.hex(),  # Guardamos en hexadecimal
            'signature': signature.hex(),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        print(f"[QUEEN] Abeja {name} creada con firma DSA.")
        return Agent(name, self, signature, data)

    def verify_agent(self, signature, data):
        try:
            self.public_key.verify(signature, data, hashes.SHA256())
            return True
        except InvalidSignature:
            return False

    def report(self, agent, file, signature, data):
        # Verifica que la abeja tenga firma válida
        if not self.verify_agent(signature, data):
            print(f"[ALERTA] Reporte rechazado de {agent} — firma inválida.")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.hive.contains((self.query.agent == agent) & (self.query.file == file)):
            self.hive.insert({'agent': agent, 'file': file, 'datetime': now})
            print(f"[QUEEN] Reporte aceptado de {agent} por {file}")
