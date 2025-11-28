# queen/queen.py
"""
Queen: motor central de BeeShield
Versión: optimizada + extendida (B + C)

Características principales:
- gui_callback opcional en report() y escaneo_manual() para enviar mensajes directos a la interfaz
- Event listeners (subscribe) para que otros módulos reciban eventos
- Soporte de debounce (agrupa reportes cercanos en tiempo)
- Sistema simple de severidad y métricas (conteo por agente/archivo/tipo)
- Detección extendida (extensiones sospechosas + whitelist + hash-known database)
- Manejo robusto de firmas (DSA) y registro de claves públicas
- Generación de PDF conservando layout previo
- Buenas prácticas de hilos y bloqueo

NOTA: esta versión asume que la función `move_to_quarantine` la llamas desde fuera (p.ej. en main.py) o que tus agentes la llaman.
"""

from tinydb import TinyDB, Query
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
from fpdf import FPDF
import threading
import os
import hashlib
import traceback


class Queen:
    """Motor principal de BeeShield.

    Diseño orientado a producción mínima:
    - Event-driven (callbacks)
    - Safe threading
    - Separación de responsabilidades (Queen no maneja GUI directamente)
    """

    # Default debounce delay (segundos) para agrupar reportes del mismo archivo
    DEBOUNCE_DELAY = 0.3

    # Lista por defecto de extensiones consideradas sospechosas
    DEFAULT_SUSPICIOUS_EXT = {'.exe', '.bat', '.js', '.vbs', '.scr', '.cmd', '.ps1', '.jar'}

    def __init__(self, db_path='hive.json'):
        # DB
        self.hive = TinyDB(db_path)
        self.query = Query()

        # DSA keys
        self.private_key = dsa.generate_private_key(key_size=2048)
        self.public_key = self.private_key.public_key()

        # Buffers y estructuras internas
        self.reports_buffer = {}          # archivo -> set(agentes)
        self._debounce_timers = {}        # archivo -> threading.Timer
        self._public_keys = {}            # agent_name -> public key object
        self._lock = threading.RLock()

        # Listeners/event system
        self._listeners = []              # callbacks que reciben (event_dict)

        # Config/whitelist/known hashes
        self.whitelist_paths = set()
        self.suspicious_ext = set(self.DEFAULT_SUSPICIOUS_EXT)
        self.known_malware_hashes = set()  # almacenar hashes SHA256 conocidos

        # Metrics
        self.metrics = {
            'reports_total': 0,
            'reports_by_agent': {},
            'reports_by_file': {},
            'last_scan_duration': None,
        }

    # ---------------------- Utilidades internas ----------------------
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
        """Enviar evento a todos los listeners registrados (no bloqueante)."""
        listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(event)
            except Exception:
                # No debe romper el motor si un listener falla
                print(f"[QUEEN] Error en listener: {traceback.format_exc()}")

    def add_listener(self, callback):
        """Registrar un callback que reciba eventos: callback(event_dict)"""
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

    # ---------------------- Firmas y agentes ----------------------
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

    # ---------------------- Reporte con debounce y GUI callback ----------------------
    def _debounced_report(self, file, gui_callback=None):
        """Se ejecuta tras debounce; guarda en BD y notifica GUI/listeners."""
        with self._lock:
            agents_list = list(self.reports_buffer.get(file, []))
            agents = ', '.join(sorted(agents_list))
            msg = f"🧩 Archivo detectado: {file}\n   → Reportado por: {agents}\n"

            # Consola
            print(msg)

            # GUI (si se pasa)
            if gui_callback and callable(gui_callback):
                try:
                    gui_callback(msg)
                except Exception:
                    print(f"[QUEEN] Error en gui_callback: {traceback.format_exc()}")

            # Registrar en DB
            timestamp = self._now()
            for ag in agents_list:
                if not self.hive.contains((self.query.agent == ag) & (self.query.file == file)):
                    self.hive.insert({'agent': ag, 'file': file, 'datetime': timestamp})

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
            self.reports_buffer[file].clear()

    def report(self, agent, file, signature=None, data=None, signed_message=None, gui_callback=None, severity='low'):
        """Recibir reporte desde agentes.

        Parámetros:
        - agent: str (nombre agente)
        - file: str (ruta)
        - signature/data/signed_message: para verificación opcional
        - gui_callback: función que recibe strings para la GUI
        - severity: 'low'|'medium'|'high' (no obligatorio)
        """
        # Validaciones básicas
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

        # Opcional: ignorar rutas en whitelist
        try:
            if self.whitelist_paths:
                # commonpath puede fallar si las rutas no son absolutas; usamos abspath
                file_abs = os.path.abspath(file)
                if any(os.path.commonpath([file_abs, w]) == w for w in self.whitelist_paths):
                    return True
        except Exception:
            # Si hay problema con commonpath, no bloqueamos el reporte
            pass

        with self._lock:
            if file not in self.reports_buffer:
                self.reports_buffer[file] = set()
            self.reports_buffer[file].add(agent)

            # Reiniciar debounce timer y pasar gui_callback
            if file in self._debounce_timers:
                try:
                    self._debounce_timers[file].cancel()
                except Exception:
                    pass

            timer = threading.Timer(self.DEBOUNCE_DELAY, self._debounced_report, args=[file, gui_callback])
            self._debounce_timers[file] = timer
            timer.start()

        return True

    # ---------------------- Escaneo manual (motor) ----------------------
    def escaneo_manual(self, ruta='tests/files', gui_callback=None, move_to_quarantine_cb=None, scan_rules=None):
        """Escaneo manual que puede ser lanzado por la UI.

        - gui_callback(message) muestra mensajes en la GUI
        - move_to_quarantine_cb(path) es callback opcional para mover archivos
        - scan_rules: dict con reglas adicionales (p.ej. {'extensions': set([...])})
        """
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

            # Merge rules
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

                    # 1) Extensión sospechosa
                    if ext in rules_ext:
                        detected = True
                        reason.append('suspicious_extension')

                    # 2) Hash conocido
                    h = self._sha256_file(filepath)
                    if h and h in self.known_malware_hashes:
                        detected = True
                        reason.append('known_hash')

                    # 3) Tamaño/exceso de cambios (puedes añadir heurística aquí)

                    if detected:
                        temp_agent = 'EscaneoManual'
                        # Reportar (envía gui_callback hacia _debounced_report vía timer)
                        self.report(temp_agent, filepath, gui_callback=gui_callback)

                        # Intentar mover a cuarentena si se proporcionó callback
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

                        # Notificar detalles
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

    # ---------------------- PDF report (mejorado) ----------------------
    def generate_pdf_report(self, filename='Hive_Report.pdf', logo_path='public/assets/bee7.png'):
        filename_abs = os.path.abspath(filename)
        pdf = FPDF()
        pdf.add_page()

        if logo_path and os.path.exists(logo_path):
            try:
                pdf.image(logo_path, x=10, y=8, w=30)
            except Exception:
                pass

        pdf.set_font('Helvetica', 'B', 16)
        pdf.cell(0, 15, 'Reporte de la Colmena - BeeCode', ln=True, align='C')
        pdf.ln(8)

        # Cabecera
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(70, 8, 'Archivo', border=1, align='C', fill=True)
        pdf.cell(60, 8, 'Agentes', border=1, align='C', fill=True)
        pdf.cell(50, 8, 'Fecha y hora', border=1, align='C', fill=True)
        pdf.ln()

        pdf.set_font('Helvetica', '', 10)

        # Usamos la DB para listar eventos recientes
        for rec in self.hive.all():
            file = rec.get('file', '')
            agent = rec.get('agent', '')
            dt = rec.get('datetime', '')
            pdf.cell(70, 8, str(file)[:60], border=1)
            pdf.cell(60, 8, str(agent)[:40], border=1)
            pdf.cell(50, 8, str(dt)[:30], border=1)
            pdf.ln()

        pdf.output(filename_abs)
        print(f"[QUEEN] PDF generado: {filename_abs}")

    # ---------------------- Helpers para administración ----------------------
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
