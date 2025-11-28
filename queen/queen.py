# queen/queen.py
"""
Queen: motor central de BeeShield
Versión: optimizada + extendida (B + C)

Incluye:
- report() / escaneo_manual() con gui_callback
- debounce de eventos
- listeners (event system)
- whitelist / known hashes / suspicious extensions
- métricas básicas
- generar_reporte_pdf -> PDF profesional con ReportLab
- generate_pdf_report -> wrapper para compatibilidad con interfaz (usa generar_reporte_pdf)
"""

from tinydb import TinyDB, Query
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
import threading
import os
import hashlib
import traceback

# ReportLab imports para PDF profesional
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# === Rutas para reportes ===
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
REPORTS_FOLDER = os.path.join(DESKTOP_PATH, "Reportes BeeShield")
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# Logo path (ajusta si tu logo está en otra carpeta)
LOGO_PATH = "public/assets/bee7.png"  # o "assets/beeshield_logo.png"

class Queen:
    """Motor principal de BeeShield."""

    DEBOUNCE_DELAY = 0.3
    DEFAULT_SUSPICIOUS_EXT = {'.exe', '.bat', '.js', '.vbs', '.scr', '.cmd', '.ps1', '.jar'}

    def __init__(self, db_path='hive.json'):
        # DB
        self.hive = TinyDB(db_path)
        self.query = Query()

        # Firmas DSA
        self.private_key = dsa.generate_private_key(key_size=2048)
        self.public_key = self.private_key.public_key()

        # Estructuras internas
        self.reports_buffer = {}          # archivo -> set(agentes)
        self._debounce_timers = {}        # archivo -> threading.Timer
        self._public_keys = {}            # agent_name -> public key object
        self._lock = threading.RLock()

        # Listeners/event system
        self._listeners = []              # callbacks que reciben (event_dict)

        # Config
        self.whitelist_paths = set()
        self.suspicious_ext = set(self.DEFAULT_SUSPICIOUS_EXT)
        self.known_malware_hashes = set()

        # Métricas
        self.metrics = {
            'reports_total': 0,
            'reports_by_agent': {},
            'reports_by_file': {},
            'last_scan_duration': None,
        }

    # ---------------------- Utilidades ----------------------
    def _now(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _sha256_file(self, path, block_size=65536):
        h = hashlib.sha256()
        try:
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(block_size), b''):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def _notify_listeners(self, event):
        listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(event)
            except Exception:
                print(f"[QUEEN] Error en listener: {traceback.format_exc()}")

    def add_listener(self, callback):
        if callable(callback):
            self._listeners.append(callback)
            return True
        return False

    def remove_listener(self, callback):
        try:
            self._listeners.remove(callback)
            return True
        except ValueError:
            return False

    # ---------------------- Firmas / agentes ----------------------
    def _generate_signature(self, agent_name):
        data = f"{agent_name}-{datetime.now().timestamp()}".encode()
        signature = self.private_key.sign(data, hashes.SHA256())
        return data, signature

    def create_agent(self, name, private_key=None):
        data, signature = self._generate_signature(name)
        rec = {
            'agent': name,
            'data': data.hex(),
            'signature': signature.hex(),
            'created_at': self._now()
        }
        self.hive.insert(rec)
        print(f"[QUEEN] Abeja '{name}' creada.")

        class _TmpAgent:
            def __init__(self, name, sig, data):
                self.name = name
                self.signature = sig
                self.data = data

        return _TmpAgent(name, signature.hex(), data.hex())

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
        try:
            sig = bytes.fromhex(signature) if isinstance(signature, str) else signature
            dat = bytes.fromhex(data) if isinstance(data, str) else data
        except ValueError:
            print(f"[QUEEN] Firma inválida (hex).")
            return False

        key = self._public_keys.get(name, self.public_key)
        try:
            key.verify(sig, dat, hashes.SHA256())
            return True
        except InvalidSignature:
            print(f"[QUEEN] Firma DSA inválida para '{name}'.")
            return False
        except Exception as e:
            print(f"[QUEEN] Error verificando firma: {e}")
            return False

    # ---------------------- Reporte / debounce / GUI callback ----------------------
    def _debounced_report(self, file, gui_callback=None):
        """Se ejecuta tras debounce; guarda en DB y notifica GUI/listeners."""
        with self._lock:
            agents_list = list(self.reports_buffer.get(file, []))
            agents = ', '.join(sorted(agents_list))
            msg = f"🧩 Archivo detectado: {file}\n   → Reportado por: {agents}\n"

            # Consola
            print(msg)

            # GUI
            if gui_callback and callable(gui_callback):
                try:
                    gui_callback(msg)
                except Exception:
                    print(f"[QUEEN] Error en gui_callback: {traceback.format_exc()}")

            # Guardar en DB
            timestamp = self._now()
            for ag in agents_list:
                try:
                    if not self.hive.contains((self.query.agent == ag) & (self.query.file == file)):
                        self.hive.insert({'agent': ag, 'file': file, 'datetime': timestamp})
                except Exception:
                    # tinydb exceptions pueden ocurrir si schema cambia; evitamos romper
                    print(f"[QUEEN] Error insertando en DB: {traceback.format_exc()}")

            # Actualizar métricas
            num_reports = len(agents_list)
            self.metrics['reports_total'] += num_reports
            self.metrics['reports_by_file'][file] = self.metrics['reports_by_file'].get(file, 0) + num_reports
            for ag in agents_list:
                self.metrics['reports_by_agent'][ag] = self.metrics['reports_by_agent'].get(ag, 0) + 1

            # Emitir evento a listeners (no bloqueante)
            event = {
                'type': 'file_detected',
                'file': file,
                'agents': agents_list,
                'timestamp': timestamp
            }
            try:
                threading.Thread(target=self._notify_listeners, args=(event,), daemon=True).start()
            except Exception:
                print(f"[QUEEN] Error notificando listeners: {traceback.format_exc()}")

            # Limpiar
            try:
                del self._debounce_timers[file]
            except KeyError:
                pass
            try:
                self.reports_buffer[file].clear()
            except Exception:
                pass

    def report(self, agent, file, signature=None, data=None, signed_message=None, gui_callback=None, severity='low'):
        """Recibir reporte desde agentes."""
        if signature and signed_message:
            if not self.verify_agent(agent, signature, signed_message):
                err = f"[ALERTA] Reporte rechazado de '{agent}' — firma inválida."
                print(err)
                if gui_callback and callable(gui_callback):
                    try:
                        gui_callback(err)
                    except Exception:
                        print(f"[QUEEN] Error gui_callback (alert): {traceback.format_exc()}")
                return False

        if not file:
            return False

        # Ignorar rutas en whitelist (si aplica)
        try:
            if self.whitelist_paths:
                file_abs = os.path.abspath(file)
                if any(os.path.commonpath([file_abs, w]) == w for w in self.whitelist_paths):
                    return True
        except Exception:
            pass

        with self._lock:
            if file not in self.reports_buffer:
                self.reports_buffer[file] = set()
            self.reports_buffer[file].add(agent)

            # Reiniciar timer
            if file in self._debounce_timers:
                try:
                    self._debounce_timers[file].cancel()
                except Exception:
                    pass

            timer = threading.Timer(self.DEBOUNCE_DELAY, self._debounced_report, args=[file, gui_callback])
            self._debounce_timers[file] = timer
            timer.start()

        return True

    # ---------------------- Escaneo manual ----------------------
    def escaneo_manual(self, ruta='tests/files', gui_callback=None, move_to_quarantine_cb=None, scan_rules=None):
        """Escaneo manual que puede ser lanzado por la UI."""
        start_ts = datetime.now()
        try:
            if not os.path.exists(ruta):
                msg = f"[ESCANEO] Ruta no encontrada: {ruta}"
                print(msg)
                if gui_callback and callable(gui_callback):
                    try:
                        gui_callback(msg)
                    except Exception:
                        print(f"[QUEEN] Error gui_callback (ruta): {traceback.format_exc()}")
                return

            # Reglas de extensiones
            rules_ext = set(self.suspicious_ext)
            if scan_rules and 'extensions' in scan_rules:
                rules_ext.update(scan_rules['extensions'])

            archivos = []
            for root, _, files in os.walk(ruta):
                for f in files:
                    archivos.append(os.path.join(root, f))

            msg = f"[ESCANEO] Analizando {len(archivos)} archivos en {ruta}"
            print(msg)
            if gui_callback and callable(gui_callback):
                try:
                    gui_callback(msg)
                except Exception:
                    print(f"[QUEEN] Error gui_callback (inicio): {traceback.format_exc()}")

            for filepath in archivos:
                try:
                    # Saltar si está en whitelist
                    if self.whitelist_paths:
                        try:
                            file_abs = os.path.abspath(filepath)
                            if any(os.path.commonpath([file_abs, w]) == w for w in self.whitelist_paths):
                                continue
                        except Exception:
                            pass

                    _, ext = os.path.splitext(filepath)
                    ext = ext.lower()

                    detected = False
                    reason = []

                    if ext in rules_ext:
                        detected = True
                        reason.append('suspicious_extension')

                    h = self._sha256_file(filepath)
                    if h and h in self.known_malware_hashes:
                        detected = True
                        reason.append('known_hash')

                    if detected:
                        temp_agent = 'EscaneoManual'
                        self.report(temp_agent, filepath, gui_callback=gui_callback)

                        # Mover a cuarentena si se proporcionó callback
                        if move_to_quarantine_cb and callable(move_to_quarantine_cb):
                            try:
                                move_to_quarantine_cb(filepath)
                                if gui_callback and callable(gui_callback):
                                    try:
                                        gui_callback(f"[CUARENTENA] Movido: {filepath}")
                                    except Exception:
                                        print(f"[QUEEN] Error gui_callback (cuarentena): {traceback.format_exc()}")
                            except Exception:
                                if gui_callback and callable(gui_callback):
                                    try:
                                        gui_callback(f"[CUARENTENA] Error moviendo: {filepath}")
                                    except Exception:
                                        print(f"[QUEEN] Error gui_callback (cuarentena-exc): {traceback.format_exc()}")

                        detalle = f"[DETECTADO] {filepath} -> {', '.join(reason)}"
                        print(detalle)
                        if gui_callback and callable(gui_callback):
                            try:
                                gui_callback(detalle)
                            except Exception:
                                print(f"[QUEEN] Error gui_callback (detalle): {traceback.format_exc()}")

                except Exception:
                    print(f"[QUEEN] Error escaneando {filepath}: {traceback.format_exc()}")

        finally:
            dur = (datetime.now() - start_ts).total_seconds()
            self.metrics['last_scan_duration'] = dur
            fin = f"[ESCANEO] Completado en {dur:.2f}s"
            print(fin)
            if gui_callback and callable(gui_callback):
                try:
                    gui_callback(fin)
                except Exception:
                    print(f"[QUEEN] Error gui_callback (fin): {traceback.format_exc()}")

    # ---------------------- PDF profesional (ReportLab) ----------------------
    def generar_reporte_pdf(self, titulo_reporte: str, eventos: list):
        """
        Genera un PDF profesional y lo guarda en REPORTS_FOLDER con nombre ordenable:
        BeeShield_Report_YYYY-MM-DD_HH-MM-SS.pdf
        eventos: lista de dicts con keys: datetime, agent, file, details
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"BeeShield_Report_{timestamp}.pdf"
        filepath = os.path.join(REPORTS_FOLDER, filename)

        styles = getSampleStyleSheet()
        style_title = styles["Title"]
        style_normal = styles["BodyText"]

        style_summary = ParagraphStyle(
            'Summary',
            parent=styles['Heading2'],
            spaceAfter=14,
            textColor=colors.HexColor("#333333")
        )

        style_table_header = ParagraphStyle(
            'TableHeader',
            parent=styles['Heading4'],
            textColor=colors.white,
            alignment=1,
        )

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=60,
            bottomMargin=40
        )

        story = []

        # Portada
        if os.path.exists(LOGO_PATH):
            try:
                img = Image(LOGO_PATH, width=120, height=120)
                img.hAlign = "CENTER"
                story.append(img)
                story.append(Spacer(1, 18))
            except Exception:
                pass

        story.append(Paragraph(f"<b>{titulo_reporte}</b>", style_title))
        story.append(Spacer(1, 12))

        fecha_actual = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
        story.append(Paragraph(f"Generado: {fecha_actual}", style_normal))
        story.append(Spacer(1, 18))

        story.append(Paragraph("<b>Resumen Ejecutivo</b>", style_summary))
        story.append(Spacer(1, 6))

        total_eventos = len(eventos)
        story.append(Paragraph(
            f"Este reporte contiene <b>{total_eventos}</b> eventos registrados por BeeShield.",
            style_normal
        ))
        story.append(Spacer(1, 12))
        story.append(PageBreak())

        # Tabla de eventos
        story.append(Paragraph("<b>Eventos Detectados</b>", styles["Heading2"]))
        story.append(Spacer(1, 12))

        data = [
            [
                Paragraph("<b>Fecha/Hora</b>", style_table_header),
                Paragraph("<b>Agente</b>", style_table_header),
                Paragraph("<b>Archivo</b>", style_table_header),
                Paragraph("<b>Detalles</b>", style_table_header)
            ]
        ]

        for e in eventos:
            data.append([
                e.get("datetime", ""),
                e.get("agent", ""),
                e.get("file", ""),
                e.get("details", "—")
            ])

        tabla = Table(data, colWidths=[110, 100, 170, 150])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),

            ("ALIGN", (0, 0), (-1, -1), "LEFT"),

            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),

            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
        ]))

        story.append(tabla)
        story.append(Spacer(1, 18))

        # Footer callback
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#555555"))
            canvas.drawString(40, 25, "BeeShield Antivirus — Reporte generado automáticamente")
            canvas.drawRightString(letter[0] - 40, 25, f"Página {doc.page}")
            canvas.restoreState()

        # Build
        try:
            doc.build(story, onFirstPage=footer, onLaterPages=footer)
            print(f"[BeeShield] Reporte profesional generado: {filepath}")
            return filepath
        except Exception:
            print(f"[QUEEN] Error generando PDF profesional: {traceback.format_exc()}")
            return None

    # Wrapper para compatibilidad (interfaz llama generate_pdf_report)
    def generate_pdf_report(self, filename=None, logo_path=None):
        """
        Compatibilidad: arma eventos desde la BD y llama al generador profesional.
        Si filename se pasa, intenta usar ese nombre dentro de REPORTS_FOLDER (sin sobreescribir).
        """
        # Armar lista de eventos desde la DB
        eventos = []
        for rec in self.hive.all():
            eventos.append({
                'datetime': rec.get('datetime', ''),
                'agent': rec.get('agent', ''),
                'file': rec.get('file', ''),
                'details': rec.get('details', '')
            })

        titulo = "Reporte de la Colmena - BeeCode"
        # Llama al generador profesional
        ruta = self.generar_reporte_pdf(titulo, eventos)
        return ruta

    # ---------------------- Helpers ----------------------
    def add_to_whitelist(self, path):
        self.whitelist_paths.add(os.path.abspath(path))

    def remove_from_whitelist(self, path):
        try:
            self.whitelist_paths.remove(os.path.abspath(path))
        except KeyError:
            pass

    def add_known_hash(self, sha256_hex):
        self.known_malware_hashes.add(sha256_hex.lower())

    def set_suspicious_extensions(self, ext_iterable):
        self.suspicious_ext = set(ext_iterable)

    def get_metrics(self):
        return dict(self.metrics)

# Fin de queen/queen.py
