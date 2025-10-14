# queen/queen.py
from tinydb import TinyDB, Query
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
from agents.agent import Agent
from fpdf import FPDF
import threading, os

class Queen:
    DEBOUNCE_DELAY = 0.3  # segundos para consolidar eventos

    def __init__(self):
        self.hive = TinyDB('hive.json')
        self.query = Query()
        self.private_key = dsa.generate_private_key(key_size=2048)
        self.public_key = self.private_key.public_key()
        self.reports_buffer = {}           # archivo -> set(agentes)
        self._debounce_timers = {}         # archivo -> timer
        self._public_keys = {}             # agent_name -> clave pública
        self._lock = threading.Lock()

    # ------------------- Agentes internos -------------------
    def _generate_signature(self, agent_name):
        data = f"{agent_name}-{datetime.now().timestamp()}".encode()
        signature = self.private_key.sign(data, hashes.SHA256())
        return data, signature

    def create_agent(self, name, private_key=None):
        """Crea un agente interno con firma DSA"""
        data, signature = self._generate_signature(name)
        self.hive.insert({
            'agent': name,
            'data': data.hex(),
            'signature': signature.hex(),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        print(f"[QUEEN] Abeja '{name}' creada con firma interna DSA.")
        return Agent(name, self, signature.hex(), data.hex(), private_key)

    # ------------------- Claves públicas externas -------------------
    def register_public_key(self, agent_name, public_pem_bytes):
        try:
            pub = serialization.load_pem_public_key(public_pem_bytes)
            with self._lock:
                self._public_keys[agent_name] = pub
            print(f"[QUEEN] Clave pública registrada para '{agent_name}'.")
            return True
        except Exception as e:
            print(f"[QUEEN] Error al registrar clave pública: {e}")
            return False

    def verify_agent(self, name, signature, data):
        """Verifica firma DSA, interna o externa"""
        try:
            sig_bytes = bytes.fromhex(signature) if isinstance(signature, str) else signature
            data_bytes = bytes.fromhex(data) if isinstance(data, str) else data
        except ValueError:
            print(f"[ALERTA] Firma inválida para '{name}' (hex incorrecto).")
            return False

        key = self._public_keys.get(name, self.public_key)
        try:
            key.verify(sig_bytes, data_bytes, hashes.SHA256())
            return True
        except InvalidSignature:
            print(f"[ALERTA] Firma DSA inválida para '{name}'.")
            return False

    # ------------------- Reportes de agentes -------------------
    def _debounced_report(self, file):
        with self._lock:
            agents = ', '.join(sorted(self.reports_buffer[file]))
            print(f"\n🧩 Archivo detectado: {file}\n   → Reportado por: {agents}\n")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for agent in self.reports_buffer[file]:
                if not self.hive.contains((self.query.agent == agent) & (self.query.file == file)):
                    self.hive.insert({'agent': agent, 'file': file, 'datetime': timestamp})
            del self._debounce_timers[file]
            self.reports_buffer[file].clear()

    def report(self, agent, file, signature=None, data=None, signed_message=None):
        """
        Agrega un reporte al buffer.
        - signature + signed_message para agentes externos
        """
        if signature and signed_message:
            if not self.verify_agent(agent, signature, signed_message):
                print(f"[ALERTA] Reporte rechazado de '{agent}' — firma inválida.")
                return False
        if not file:
            return
        with self._lock:
            if file not in self.reports_buffer:
                self.reports_buffer[file] = set()
            self.reports_buffer[file].add(agent)

            # reiniciar timer de debounce
            if file in self._debounce_timers:
                self._debounce_timers[file].cancel()
            timer = threading.Timer(self.DEBOUNCE_DELAY, self._debounced_report, args=[file])
            self._debounce_timers[file] = timer
            timer.start()
        return True

    # ------------------- Generar reporte PDF -------------------
    def generate_pdf_report(self, filename="Hive_Report.pdf", logo_path="public/assets/bee7.png"):
        filename_abs = os.path.abspath(filename)
        pdf = FPDF()
        pdf.add_page()

        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=30)

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 15, "Reporte de la Colmena - BeeCode", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(60, 10, "Archivo", border=1, align="C", fill=True)
        pdf.cell(80, 10, "Agentes", border=1, align="C", fill=True)
        pdf.cell(50, 10, "Fecha y hora", border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 12)
        fill = False
        for file, agents in self.reports_buffer.items():
            record = self.hive.get(self.query.file == file)
            timestamp = record.get("datetime") if record else ""
            agents_str = ', '.join(sorted(agents))
            pdf.set_fill_color(240, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(60, 10, file, border=1, fill=True)
            pdf.cell(80, 10, agents_str, border=1, fill=True)
            pdf.cell(50, 10, timestamp, border=1, fill=True)
            pdf.ln()
            fill = not fill

        pdf.output(filename_abs)
        print(f"[QUEEN] Reporte PDF generado: {filename_abs}")
