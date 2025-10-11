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
        self.reports_buffer = {}  # Para agrupar reportes visualmente

    def _generate_signature(self, name):
        # Genera datos a firmar (únicos por abeja)
        data = f"{name}-{datetime.now().timestamp()}".encode()
        signature = self.private_key.sign(data, hashes.SHA256())
        return data, signature

    def create_agent(self, name):
        data, signature = self._generate_signature(name)
        # Guardar en base en formato hexadecimal
        self.hive.insert({
            'agent': name,
            'data': data.hex(),
            'signature': signature.hex(),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        print(f"[QUEEN] Abeja {name} creada con firma DSA.")
        # Pasamos la firma y los datos ya en hex
        return Agent(name, self, signature.hex(), data.hex())

    def verify_agent(self, name, signature, data):
        """Verifica que la firma DSA sea válida."""
        try:
            signature_bytes = bytes.fromhex(signature)
            data_bytes = bytes.fromhex(data)
        except ValueError:
            print(f"[ALERTA] Firma inválida para {name}")
            return False

        try:
            self.public_key.verify(signature_bytes, data_bytes, hashes.SHA256())
            return True
        except InvalidSignature:
            return False

    def report(self, agent, file, signature, data):
        """Recibe los reportes de las abejas y los valida."""
        if not self.verify_agent(agent, signature, data):
            print(f"[ALERTA] Reporte rechazado de {agent} — firma inválida.")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 🔹 Agrupar reportes por archivo
        if file not in self.reports_buffer:
            self.reports_buffer[file] = set()

        self.reports_buffer[file].add(agent)

        # 🔹 Mostrar resumen ordenado y limpio
        agents_involved = ', '.join(sorted(self.reports_buffer[file]))
        print(f"\n🧩 Archivo modificado: {file}\n   → Reportado por: {agents_involved}\n")

        # 🔹 Guardar en base de datos (solo una vez por agente y archivo)
        if not self.hive.contains((self.query.agent == agent) & (self.query.file == file)):
            self.hive.insert({
                'agent': agent,
                'file': file,
                'datetime': now
            })
