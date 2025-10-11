from tinydb import TinyDB, Query
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from agents.agent import Agent
from fpdf import FPDF
import os

class Queen:
    def __init__(self):
        self.hive = TinyDB('hive.json')
        self.query = Query()
        self.private_key = dsa.generate_private_key(key_size=2048)
        self.public_key = self.private_key.public_key()
        self.reports_buffer = {}

    def _generate_signature(self, name):
        data = f"{name}-{datetime.now().timestamp()}".encode()
        signature = self.private_key.sign(data, hashes.SHA256())
        return data, signature

    def create_agent(self, name):
        data, signature = self._generate_signature(name)
        self.hive.insert({
            'agent': name,
            'data': data.hex(),
            'signature': signature.hex(),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        print(f"[QUEEN] Abeja {name} creada con firma DSA.")
        return Agent(name, self, signature.hex(), data.hex())

    def verify_agent(self, name, signature, data):
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
        if not self.verify_agent(agent, signature, data):
            print(f"[ALERTA] Reporte rechazado de {agent} — firma inválida.")
            return

        # 🔹 No reportar si no hay archivo
        if not file:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if file not in self.reports_buffer:
            self.reports_buffer[file] = set()
        self.reports_buffer[file].add(agent)

        agents_involved = ', '.join(sorted(self.reports_buffer[file]))
        print(f"\n🧩 Archivo modificado: {file}\n   → Reportado por: {agents_involved}\n")

        # 🔹 Insertar solo si no existe
        if not self.hive.contains((self.query.agent == agent) & (self.query.file == file)):
            self.hive.insert({'agent': agent, 'file': file, 'datetime': now})

    def generate_pdf_report(self, filename="Hive_Report.pdf", logo_path="public/assets/bee7.png"):
        # Ruta absoluta para evitar problemas de permisos
        filename_abs = os.path.abspath(filename)

        pdf = FPDF()
        pdf.add_page()

        # 🔹 Logo
        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=30)

        # 🔹 Encabezado
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 15, "Reporte de la Colmena - BeeCode", ln=True, align="C")
        pdf.ln(10)

        # 🔹 Encabezado tabla
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(60, 10, "Archivo", border=1, align="C", fill=True)
        pdf.cell(80, 10, "Agentes", border=1, align="C", fill=True)
        pdf.cell(50, 10, "Fecha y hora", border=1, align="C", fill=True)
        pdf.ln()

        # 🔹 Filas alternadas
        pdf.set_font("Helvetica", "", 12)
        fill = False
        for file, agents in self.reports_buffer.items():
            record = self.hive.get(self.query.file == file)
            datetime_str = record.get("datetime") if record else ""
            agents_str = ', '.join(sorted(agents))
            pdf.set_fill_color(240, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(60, 10, file, border=1, fill=True)
            pdf.cell(80, 10, agents_str, border=1, fill=True)
            pdf.cell(50, 10, datetime_str, border=1, fill=True)
            pdf.ln()
            fill = not fill

        pdf.output(filename_abs)
        print(f"[QUEEN] Reporte PDF generado: {filename_abs}")
