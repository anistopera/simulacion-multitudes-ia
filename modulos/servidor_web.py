"""Interfaz web local del simulador. Solo librería estándar de Python.

Python conserva toda la lógica (simulación, diagnóstico, métricas). El navegador
solo dibuja lo que recibe y envía órdenes de control.

    python -m modulos.servidor_web            # inicia la interfaz (sin flags)
    python main.py --interfaz                 # equivalente
    python -m modulos.servidor_web --prueba   # autoprueba corta, sin navegador

Cómo se conecta con la simulación: la clase SesionWeb tiene los mismos métodos que
la vista de pygame (procesar_eventos, dibujar, cerrar) más tick y conectar. Se le
pasa a main.ejecutar_episodio(..., vista=sesion), de modo que la interfaz web
ejecuta exactamente el mismo ciclo que las corridas por lotes.

Endpoints: GET /config (mapa, una vez), GET /estado,
POST /control (órdenes). /estado?desde=N espera hasta 0,5 s a que haya un estado
nuevo; si no lo hay responde 204, así el navegador no trabaja cuando nada cambia. Los archivos de web/ se leen del disco en cada petición.
"""
import argparse
import json
import math
import platform
import subprocess
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import numpy as np

from modulos.dbscan_deteccion import clasificar_puntos
from modulos.diagnostico import ESTADO_CRITICA
from modulos.entorno import Entorno

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / 'web'
PUERTO = 8765
MODO_PSO = 'B_PSO'        # identificador real de main.py; la interfaz lo muestra como B+PSO
MODOS = ('A', 'B', MODO_PSO)
VELOCIDADES = (1, 2, 4)   # solo cambia el ritmo del reloj; el paso físico sigue en 0.1 s
MAX_PASOS_PENDIENTES = 5  # al mantener pulsada la tecla de paso
ARCHIVO_THETA = RAIZ / 'capturas' / 'theta_optimo.json'
HTML, CSS, JS = ('text/html; charset=utf-8', 'text/css; charset=utf-8',
                 'text/javascript; charset=utf-8')
# Lista blanca: solo estos archivos de web/ se sirven; nada más del repositorio.
ESTATICOS = {'/': ('index.html', HTML), '/index.html': ('index.html', HTML),
             '/estilos.css': ('estilos.css', CSS), '/app.js': ('app.js', JS)}
# Todo debe venir de este mismo servidor: la interfaz no usa recursos externos.
POLITICA = "default-src 'self'; img-src 'self' data: blob:; connect-src 'self'"


class SesionWeb:
    """Un episodio a la vez, ejecutado en un hilo, controlado desde el navegador."""

    def __init__(self, principal, modo='A', escenario='S1', semilla=42):
        self.principal = principal                    # módulo main (o equivalente)
        self.escenarios = dict(principal.ESCENARIOS)  # {'S1': 40, 'S2': 80, 'S3': 120}
        self._cv = threading.Condition()              # protege el estado compartido
        self._orden = threading.Lock()                # un comando a la vez
        self._tmp = tempfile.TemporaryDirectory(prefix='multitudes_ui_')
        self._hilo = None
        self._siguiente = 0.0                         # hora del próximo tick
        self._velocidad = 1
        self._seq = 0                                 # sube con cada estado nuevo
        self._pso_visto = None
        self._ultima_publicacion = 0.0
        self._dt_medio = 0.1                          # segundos reales por tick
        entorno = Entorno(configuracion=str(principal.CARPETA / 'configuracion.json'))
        self._config = {
            'ancho': entorno.ancho, 'alto': entorno.alto, 'tam_celda': entorno.tam_celda,
            'entrada': list(entorno.entrada), 'salida': list(entorno.salida),
            # esquina inferior izquierda (x, y) en metros de cada celda bloqueada
            'obstaculos': [[int(c) * entorno.tam_celda, int(f) * entorno.tam_celda]
                           for f, c in entorno.obstaculos()],
            'modos': list(MODOS), 'escenarios': self.escenarios,
        }
        if modo == MODO_PSO and not self.pso_disponible()[0]:
            print(f'B+PSO no disponible: {self.pso_disponible()[1]}. Se inicia en modo A.')
            modo = 'A'
        self._reiniciar_episodio(modo, escenario, semilla)

    # ---------- consultas (hilos HTTP) ----------
    def config(self):
        return self._config

    def pso_disponible(self):
        """B+PSO exige el modo en main.py y un theta válido según main.cargar_theta."""
        if MODO_PSO not in getattr(self.principal, 'MODOS_V3', ()):
            return False, 'main.py no incluye el modo B_PSO'
        try:
            self.principal.cargar_theta(ARCHIVO_THETA)
        except FileNotFoundError:
            return False, 'falta capturas/theta_optimo.json'
        except (OSError, ValueError, KeyError, TypeError):
            return False, 'capturas/theta_optimo.json no tiene alpha, ks y kr válidos'
        return True, ''

    def esperar_cambio(self, desde, limite=0.5):
        """True si hay un estado distinto de `desde`; espera como máximo `limite` s."""
        with self._cv:
            if self._cv.wait_for(lambda: self._seq != desde, timeout=limite):
                return True
        pso = self.pso_disponible()
        with self._cv:
            if pso != self._pso_visto:   # apareció o cambió theta_optimo.json
                self._pso_visto = pso
                self._seq += 1
                return True
        return False

    def estado(self):
        with self._cv:
            snap, error, resumen, seq = self._snap, self._error, self._resumen, self._seq
            if error:
                fase = 'error'
            elif self._terminado:
                fase = 'terminado'
            elif self._pausado:
                fase = 'listo' if snap['t'] == 0 else 'pausado'
            else:
                fase = 'corriendo'
            modo, escenario, semilla = self.modo, self.escenario, self.semilla
        disponible, motivo = self.pso_disponible()
        return {**snap, 'fase': fase, 'modo': modo, 'escenario': escenario,
                'semilla': semilla, 'total': self.escenarios[escenario],
                'velocidad': self._velocidad, 'seq': seq,
                'velocidad_real': round(0.1 / self._dt_medio, 1),
                'resumen': resumen, 'error': error,
                'pso': {'disponible': disponible, 'motivo': motivo}}

    # ---------- órdenes del navegador ----------
    def comando(self, datos):
        """Ejecuta una orden de /control. ValueError si es inválida."""
        accion = datos.get('accion')
        with self._orden:
            if accion == 'iniciar':
                with self._cv:
                    if not self._terminado and not self._error:
                        self._pausado = False
                        self._cv.notify_all()
            elif accion == 'pausar':
                with self._cv:
                    self._pausado = True
            elif accion == 'paso':
                with self._cv:   # solo en pausa: avanza exactamente un tick de 0.1 s
                    if self._pausado and not self._terminado and not self._error:
                        self._pasos = min(self._pasos + 1, MAX_PASOS_PENDIENTES)
                        self._cv.notify_all()
            elif accion == 'velocidad':
                valor = datos.get('valor')
                if isinstance(valor, bool) or valor not in VELOCIDADES:
                    raise ValueError('Velocidad inválida')
                self._velocidad = valor
                self._dt_medio = 0.1 / valor
            elif accion == 'reiniciar':
                self._reiniciar_episodio(self.modo, self.escenario, self.semilla)
            elif accion == 'configurar':
                modo = datos.get('modo', self.modo)
                escenario = datos.get('escenario', self.escenario)
                semilla = datos.get('semilla', self.semilla)
                if modo not in MODOS:
                    raise ValueError('Modo inválido')
                if modo == MODO_PSO and not self.pso_disponible()[0]:
                    raise ValueError('B+PSO no disponible: ' + self.pso_disponible()[1])
                if escenario not in self.escenarios:
                    raise ValueError('Escenario inválido')
                if (isinstance(semilla, bool) or not isinstance(semilla, int)
                        or not 0 <= semilla < 2**31):
                    raise ValueError('Semilla inválida')
                self._reiniciar_episodio(modo, escenario, semilla)
            else:
                raise ValueError('Acción desconocida')
            with self._cv:
                self._seq += 1
                self._cv.notify_all()
        return self.estado()

    def cerrar_todo(self):
        self._detener()
        self._tmp.cleanup()

    # ---------- ciclo del episodio (hilo de simulación) ----------
    def _detener(self):
        hilo = self._hilo
        if hilo is not None and hilo.is_alive():
            with self._cv:
                self._cancelar = True
                self._cv.notify_all()
            hilo.join(5)

    def _reiniciar_episodio(self, modo, escenario, semilla):
        """Detiene el episodio actual y deja uno nuevo en t = 0, en pausa."""
        self._detener()
        with self._cv:
            self.modo, self.escenario, self.semilla = modo, escenario, semilla
            self._cancelar = False
            self._pausado = True
            self._pasos = 0
            self._conectado = False
            self._terminado = False
            self._error = None
            self._resumen = None
            self._dt_medio = 0.1 / self._velocidad
            self._snap = {'t': 0.0, 'reloj': round(time.monotonic(), 3), 'activos': 0,
                          'llegados': 0, 'criticas': 0, 'agentes': [], 'centros': [],
                          'densidad': []}
        self._hilo = threading.Thread(
            target=self._correr, args=(modo, self.escenarios[escenario], semilla), daemon=True)
        self._hilo.start()
        with self._cv:   # responder ya con los agentes en t = 0, sin cuadro vacío
            self._cv.wait_for(lambda: self._conectado or self._error, timeout=5)

    def _correr(self, modo, n_agentes, semilla):
        try:
            theta = self.principal.cargar_theta(ARCHIVO_THETA) if modo == MODO_PSO else None
            r = self.principal.ejecutar_episodio(
                n_agentes, modo, semilla, carpeta_salida=self._tmp.name, theta=theta, vista=self)
            with self._cv:
                if not self._cancelar:
                    self._resumen = {
                        'llegados': r['llegados'], 'total': n_agentes,
                        'tiempo': round(r['duracion_simulada_s'], 1),
                        'tasa': round(r['tasa_finalizacion_pct'], 1)}
                    self._terminado = True
                    self._seq += 1
                    self._cv.notify_all()
        except Exception as error:  # se muestra en la interfaz; Reiniciar lo recupera
            with self._cv:
                self._error = f'{type(error).__name__}: {error}'
                self._seq += 1
                self._cv.notify_all()

    # ---------- interfaz de vista que usa main.ejecutar_episodio ----------
    def conectar(self, motor, diagnostico):
        self._diagnostico = diagnostico
        self._publicar(motor.agentes_activos, 0.0, 0, diagnostico.densidad)
        with self._cv:
            self._conectado = True
            self._cv.notify_all()

    def procesar_eventos(self, eventos=None):
        """Se llama al inicio de cada tick. Bloquea en pausa; False = detener."""
        with self._cv:
            while self._pausado and self._pasos == 0 and not self._cancelar:
                self._cv.wait(0.5)
            if self._cancelar:
                return False
            if self._pausado:
                self._pasos -= 1
            return True

    def dibujar(self, agentes, tiempo_simulado, llegados=None, densidad=None):
        self._publicar(agentes, tiempo_simulado, llegados, densidad)

    def tick(self, fps):
        """Espera hasta el próximo tick: 10 por segundo a x1, 40 a x4.

        Solo decide cuándo se ejecuta el siguiente paso; no cambia dt ni la física.
        """
        ahora = time.monotonic()
        self._siguiente = max(self._siguiente + 1.0 / (fps * self._velocidad), ahora)
        if self._siguiente > ahora:
            time.sleep(self._siguiente - ahora)

    def cerrar(self):
        pass

    def _publicar(self, agentes, t, llegados, densidad):
        """Construye la instantánea completa aquí, en el hilo de simulación.

        Se reemplaza el diccionario entero (nunca se modifica), así los hilos HTTP
        siempre leen un estado coherente y nunca agentes a medio actualizar.
        """
        if round(t * 10) % 10 == 0:   # DBSCAN una vez por segundo simulado
            posiciones = np.array([[a.x, a.y] for a in agentes], dtype=float).reshape(-1, 2)
            _, tipos, clusters = clasificar_puntos(posiciones, eps=1.2, min_samples=5)
            # Por id, no por índice: entre muestras llegan agentes y la lista se acorta.
            self._tipos = {a.id: int(tipo) for a, tipo in zip(agentes, tipos)}
            self._centros = [[round(c['centro_x'], 2), round(c['centro_y'], 2), c['tamano']]
                             for c in clusters]
        filas = [[a.id, round(a.x, 2), round(a.y, 2),
                  round(math.hypot(a.vx, a.vy) / a.v_deseada, 2),
                  self._tipos.get(a.id, 0)] for a in agentes]
        criticas = int(np.count_nonzero(self._diagnostico.estados == ESTADO_CRITICA))
        ahora = time.monotonic()
        real = ahora - self._ultima_publicacion
        self._ultima_publicacion = ahora
        if 0 < real < 1:   # ritmo real sostenido; se ignoran las pausas
            self._dt_medio += 0.05 * (real - self._dt_medio)
        snap = {'t': round(float(t), 2), 'reloj': round(ahora, 3), 'activos': len(filas),
                'llegados': int(llegados), 'criticas': criticas, 'agentes': filas,
                'centros': self._centros,
                'densidad': np.round(np.asarray(densidad, dtype=float), 2).tolist()}
        with self._cv:
            self._snap = snap
            self._seq += 1
            self._cv.notify_all()


class Manejador(BaseHTTPRequestHandler):
    sesion = None   # lo fija crear_servidor
    protocol_version = 'HTTP/1.1'
    disable_nagle_algorithm = True   # envía cada respuesta sin esperar al ACK de TCP

    def log_message(self, *args):
        pass   # sin ruido en la terminal

    def _responder(self, codigo, cuerpo, tipo='application/json; charset=utf-8'):
        if isinstance(cuerpo, (dict, list)):
            cuerpo = json.dumps(cuerpo, separators=(',', ':')).encode('utf-8')
        self.send_response(codigo)
        self.send_header('Content-Type', tipo)
        if codigo != 204:
            self.send_header('Content-Length', str(len(cuerpo)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', POLITICA)
        self.end_headers()
        self.wfile.write(cuerpo)

    def _origen_valido(self):
        """Solo acepta peticiones dirigidas a 127.0.0.1/localhost (anti DNS-rebinding)
        y, si hay cabecera Origin, que sea esta misma página."""
        puerto = self.server.server_address[1]
        permitidos = {f'127.0.0.1:{puerto}', f'localhost:{puerto}'}
        origen = self.headers.get('Origin')
        return (self.headers.get('Host') in permitidos
                and (origen is None or origen in {'http://' + h for h in permitidos}))

    def do_GET(self):
        if not self._origen_valido():
            return self._responder(403, {'error': 'Host no permitido'})
        partes = urlsplit(self.path)
        ruta = partes.path
        if ruta == '/estado':
            desde = parse_qs(partes.query).get('desde', [''])[0]
            if desde.isdigit() and not self.sesion.esperar_cambio(int(desde)):
                return self._responder(204, b'')
            return self._responder(200, self.sesion.estado())
        if ruta == '/config':
            return self._responder(200, self.sesion.config())
        if ruta in ESTATICOS:
            nombre, tipo = ESTATICOS[ruta]
            try:
                return self._responder(200, (WEB / nombre).read_bytes(), tipo)
            except OSError:
                return self._responder(404, {'error': 'Archivo de web/ no encontrado'})
        self._responder(404, {'error': 'No encontrado'})

    def do_POST(self):
        if not self._origen_valido():
            return self._responder(403, {'error': 'Host no permitido'})
        if urlsplit(self.path).path != '/control':
            return self._responder(404, {'error': 'No encontrado'})
        if not (self.headers.get('Content-Type') or '').startswith('application/json'):
            return self._responder(415, {'error': 'Se requiere application/json'})
        try:
            largo = int(self.headers.get('Content-Length', ''))
        except ValueError:
            return self._responder(411, {'error': 'Falta Content-Length'})
        if not 0 < largo <= 4096:
            return self._responder(413, {'error': 'Cuerpo inválido'})
        try:
            datos = json.loads(self.rfile.read(largo))
            if not isinstance(datos, dict):
                raise ValueError('Se esperaba un objeto JSON')
            self._responder(200, self.sesion.comando(datos))
        except ValueError as error:   # incluye JSON mal formado
            self._responder(400, {'error': str(error)})


def crear_servidor(sesion, puerto=PUERTO):
    """Escucha solo en 127.0.0.1. Si el puerto está ocupado prueba los 10 siguientes."""
    clase = type('ManejadorSesion', (Manejador,), {'sesion': sesion})
    for p in (range(puerto, puerto + 11) if puerto else (0,)):
        try:
            return ThreadingHTTPServer(('127.0.0.1', p), clase)
        except OSError:
            continue
    raise OSError('No hay puerto libre cerca de %d' % puerto)


def abrir_navegador(url):
    """Mejor esfuerzo: la URL ya está impresa, por si no se abre (p. ej. en WSL)."""
    try:
        if 'microsoft' in platform.uname().release.lower():   # WSL: navegador de Windows
            subprocess.Popen(['explorer.exe', url], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        else:
            webbrowser.open(url)
    except Exception:
        pass


def servir(principal, modo='A', escenario='S1', semilla=42, puerto=PUERTO, abrir=True):
    sesion = SesionWeb(principal, modo, escenario, semilla)
    servidor = crear_servidor(sesion, puerto)
    url = f'http://127.0.0.1:{servidor.server_address[1]}/'
    print('Interfaz web lista. Abre esta dirección en el navegador (también en Windows si usas WSL):')
    print(f'    {url}')
    print('Ctrl+C para cerrar.', flush=True)
    if abrir:
        abrir_navegador(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print('\nCerrando...')
    finally:
        servidor.server_close()
        sesion.cerrar_todo()


def _prueba(principal):
    """Autoprueba: servidor real en un puerto libre, sin navegador."""
    import urllib.request

    sesion = SesionWeb(principal, 'A', 'S1', 42)
    servidor = crear_servidor(sesion, 0)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{servidor.server_address[1]}'

    def get(ruta):
        return json.load(urllib.request.urlopen(base + ruta, timeout=5))

    def post(datos):
        pedido = urllib.request.Request(base + '/control', json.dumps(datos).encode(),
                                        {'Content-Type': 'application/json'})
        return json.load(urllib.request.urlopen(pedido, timeout=10))

    def esperar(condicion, limite=10.0):
        fin = time.monotonic() + limite
        while time.monotonic() < fin:
            estado = get('/estado')
            if condicion(estado):
                return estado
            time.sleep(0.05)
        raise AssertionError('Tiempo agotado; último estado: %s' % {
            k: v for k, v in estado.items() if k not in ('agentes', 'densidad')})

    try:
        config = get('/config')
        assert (config['ancho'], config['alto']) == (30, 20) and len(config['obstaculos']) == 15
        estado = esperar(lambda e: len(e['agentes']) == 40)
        assert estado['fase'] == 'listo' and estado['t'] == 0 and estado['total'] == 40
        post({'accion': 'iniciar'})
        estado = esperar(lambda e: e['t'] >= 1.0)
        assert estado['fase'] == 'corriendo'
        post({'accion': 'pausar'})
        time.sleep(0.4)
        t1 = get('/estado')['t']
        time.sleep(0.5)
        assert get('/estado')['t'] == t1, 'En pausa el tiempo no debe avanzar'
        estado = post({'accion': 'configurar', 'escenario': 'S2'})
        estado = esperar(lambda e: len(e['agentes']) == 80)
        assert estado['t'] == 0 and estado['total'] == 80 and estado['fase'] == 'listo'
        estado = post({'accion': 'reiniciar'})
        assert estado['t'] == 0 and estado['fase'] == 'listo'
        try:
            post({'accion': 'configurar', 'modo': 'Z'})
            raise AssertionError('Un modo inválido debe rechazarse')
        except urllib.error.HTTPError as error:
            assert error.code == 400
        print('Autoprueba del servidor web: OK (puerto %d)' % servidor.server_address[1])
    finally:
        servidor.shutdown()
        servidor.server_close()
        sesion.cerrar_todo()


if __name__ == '__main__':
    import main as principal   # se ejecuta desde la raíz: python -m modulos.servidor_web

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--prueba', action='store_true', help='Autoprueba corta y termina')
    parser.add_argument('--no-abrir', action='store_true', help='No intentar abrir el navegador')
    parser.add_argument('--puerto', type=int, default=PUERTO)
    parser.add_argument('--modo', choices=MODOS, default='A')
    parser.add_argument('--escenario', choices=tuple(principal.ESCENARIOS), default='S1')
    parser.add_argument('--semilla', type=int, default=42)
    args = parser.parse_args()
    if args.prueba:
        _prueba(principal)
    else:
        servir(principal, args.modo, args.escenario, args.semilla, args.puerto,
               abrir=not args.no_abrir)
