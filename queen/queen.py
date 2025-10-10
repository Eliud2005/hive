from tinydb import TinyDB, Query
from datetime import datetime
import hashlib
from agents.agent import Agent  # Importa la clase Agent

class Queen:
    def __init__(self):
        self.hive = TinyDB('hive.json')
        self.query = Query()

    def _generate_signature(self, name):
        # Genera una firma única basada en el nombre + fecha
        data = f"{name}-{datetime.now().timestamp()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def create_agent(self, name):
        signature = self._generate_signature(name)
        # Guarda la firma en la base
        self.hive.insert({'agent': name, 'signature': signature, 'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        print(f"[QUEEN] Abeja {name} creada con firma: {signature[:10]}...")
        return Agent(name, self, signature)

    def verify_agent(self, name, signature):
        result = self.hive.get((self.query.agent == name) & (self.query.signature == signature))
        return result is not None

    def report(self, agent, file, signature):
        # Verifica que la abeja tenga firma válida
        if not self.verify_agent(agent, signature):
            print(f"[ALERTA] Reporte rechazado de {agent} — firma inválida.")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.hive.contains((self.query.agent == agent) & (self.query.file == file)):
            self.hive.insert({'agent': agent, 'file': file, 'datetime': now})
            print(f"[QUEEN] Reporte aceptado de {agent} por {file}")
