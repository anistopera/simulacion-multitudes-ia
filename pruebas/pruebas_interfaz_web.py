"""Interfaz web sin navegador: controles, contrato PSO, DBSCAN y seguridad HTTP."""
import http.client
import json
from pathlib import Path
import re
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

import main
from modulos import servidor_web
from modulos.dbscan_deteccion import TIPO_FRONTERA, TIPO_NUCLEO, TIPO_RUIDO
from modulos.servidor_web import MODO_PSO, SesionWeb, crear_servidor

RAIZ = Path(__file__).resolve().parents[1]
CAPTURAS_INICIALES = {p for p in (RAIZ / 'capturas').rglob('*') if p.is_file()}
METRICAS = ('ticks', 'tiempo_transito', 'tiempo_espera', 'solapamientos', 'llegados',
            'activos_final', 'celdas_criticas_max', 'cambios_ruta', 'recalculos_astar',
            'filas_telemetria')


def principal_corto(duracion=3.0, **cambios):
    """El main real con episodios cortos; registra resultados y theta recibidos."""
    resultados, thetas = [], []

    def ejecutar(*args, **kwargs):
        thetas.append(kwargs.get('theta'))
        resultado = main.ejecutar_episodio(*args, duracion=duracion, **kwargs)
        resultados.append(resultado)
        return resultado

    datos = dict(ESCENARIOS=main.ESCENARIOS, CARPETA=main.CARPETA, MODOS_V3=main.MODOS_V3,
                 cargar_theta=main.cargar_theta, ejecutar_episodio=ejecutar,
                 resultados=resultados, thetas=thetas)
    datos.update(cambios)
    return SimpleNamespace(**datos)


def esperar(sesion, condicion, limite=15.0):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        estado = sesion.estado()
        if condicion(estado):
            return estado
        time.sleep(0.01)
    raise AssertionError(f"Tiempo agotado en fase {estado['fase']}, t={estado['t']}")


def esperar_rutas(sesion, vistas, limite=5.0):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        estado = sesion.estado(vistas)
        if 'rutas' in estado:
            return estado
        time.sleep(0.01)
    raise AssertionError('No llegaron rutas nuevas')


class PruebasSesion(unittest.TestCase):
    def crear(self, principal, modo='A', escenario='S1', semilla=42):
        sesion = SesionWeb(principal, modo, escenario, semilla)
        self.addCleanup(sesion.cerrar_todo)
        return sesion

    def correr_hasta_el_final(self, sesion):
        sesion.comando({'accion': 'velocidad', 'valor': 4})
        sesion.comando({'accion': 'iniciar'})
        return esperar(sesion, lambda e: e['fase'] in ('terminado', 'error'))

    def test_metricas_identicas_a_lotes(self):
        for modo in ('A', 'B'):
            with self.subTest(modo=modo), tempfile.TemporaryDirectory() as carpeta:
                base = main.ejecutar_episodio(40, modo, 42, duracion=3.0, carpeta_salida=carpeta)
                principal = principal_corto()
                sesion = self.crear(principal, modo)
                self.assertEqual(self.correr_hasta_el_final(sesion)['fase'], 'terminado')
                for clave in METRICAS:
                    self.assertEqual(principal.resultados[-1][clave], base[clave], clave)

    def test_pausa_paso_reinicio_y_cambios(self):
        sesion = self.crear(principal_corto(5.0))
        self.assertEqual(sesion.estado()['fase'], 'listo')
        time.sleep(0.2)
        self.assertEqual(sesion.estado()['t'], 0)
        sesion.comando({'accion': 'paso'})
        estado = esperar(sesion, lambda e: e['t'] > 0)
        self.assertEqual((estado['t'], estado['fase']), (0.1, 'pausado'))
        time.sleep(0.2)
        self.assertEqual(sesion.estado()['t'], 0.1)
        for orden, campo, valor in (({'accion': 'reiniciar'}, 'modo', 'A'),
                                    ({'accion': 'configurar', 'modo': 'B'}, 'modo', 'B'),
                                    ({'accion': 'configurar', 'escenario': 'S2'}, 'escenario', 'S2'),
                                    ({'accion': 'configurar', 'semilla': 43}, 'semilla', 43)):
            with self.subTest(orden=orden):
                sesion.comando({'accion': 'paso'})
                esperar(sesion, lambda e: e['t'] > 0)
                estado = sesion.comando(orden)
                self.assertEqual((estado['t'], estado['fase'], estado[campo]), (0, 'listo', valor))
                self.assertEqual(len(estado['agentes']), estado['total'])

    def test_pso_rechazado_sin_requisitos_y_aceptado_con_ellos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / 'theta_optimo.json'
            with patch.object(servidor_web, 'ARCHIVO_THETA', archivo):
                sesion = self.crear(principal_corto(0.5))
                orden = {'accion': 'configurar', 'modo': MODO_PSO}
                with self.assertRaisesRegex(ValueError, 'falta'):
                    sesion.comando(orden)
                archivo.write_text('{"theta": {"alpha": 9, "ks": 1, "kr": 1}}', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'válidos'):
                    sesion.comando(orden)
                archivo.write_text('no es json', encoding='utf-8')
                self.assertFalse(sesion.estado()['pso']['disponible'])
                archivo.write_text('{"theta": {"alpha": 2, "ks": 1.5, "kr": 1}}', encoding='utf-8')
                sin_modo = self.crear(principal_corto(0.5, MODOS_V3=('A', 'B')))
                with self.assertRaisesRegex(ValueError, 'no incluye'):
                    sin_modo.comando(orden)
                self.assertTrue(sesion.estado()['pso']['disponible'])
                estado = sesion.comando(orden)
                self.assertEqual((estado['modo'], estado['t'], estado['error']), (MODO_PSO, 0, None))
                self.assertEqual(sesion.principal.thetas[-1], (2.0, 1.5, 1.0))
                self.assertEqual(self.correr_hasta_el_final(sesion)['fase'], 'terminado')

    def test_dbscan_una_vez_por_segundo_simulado(self):
        with patch.object(servidor_web, 'clasificar_puntos',
                          wraps=servidor_web.clasificar_puntos) as dbscan:
            sesion = self.crear(principal_corto(3.0))
            self.correr_hasta_el_final(sesion)
        self.assertEqual(dbscan.call_count, 4)   # t = 0, 1, 2 y 3 s

    def test_tipos_se_conservan_por_id_tras_llegadas(self):
        sesion = self.crear(principal_corto())
        puntos = {10: (5, 5), 11: (5.3, 5), 12: (5, 5.3), 13: (5.3, 5.3), 14: (5.15, 5.15),
                  15: (6.4, 5.15), 16: (20, 15)}
        agentes = [SimpleNamespace(id=i, x=x, y=y, vx=0.0, vy=0.0, v_deseada=1.0)
                   for i, (x, y) in puntos.items()]
        esperados = {i: TIPO_NUCLEO for i in range(10, 15)}
        esperados.update({15: TIPO_FRONTERA, 16: TIPO_RUIDO})
        densidad = np.zeros((10, 15))
        sesion._publicar(agentes, 1.0, 0, densidad)
        sesion._publicar(agentes[1:], 1.1, 1, densidad)   # llega el primero
        tipos = {fila[0]: fila[4] for fila in sesion.estado()['agentes']}
        esperados.pop(10)
        self.assertEqual(tipos, esperados)

    def test_rutas_solo_si_se_piden_y_una_vez_por_segundo(self):
        sesion = self.crear(principal_corto(3.0))
        self.assertNotIn('rutas', sesion.estado())
        sesion.pedir_rutas()
        estado = esperar_rutas(sesion, '')
        version = estado['rutas_v']
        self.assertEqual({r[0] for r in estado['rutas']}, {a[0] for a in estado['agentes']})
        for _, ruta in estado['rutas']:
            self.assertTrue(ruta)
            self.assertTrue(all(len(p) == 2 and 0 <= p[0] <= 30 and 0 <= p[1] <= 20 for p in ruta))
        self.assertNotIn('rutas', sesion.estado())
        self.assertNotIn('rutas', sesion.estado(str(version)))
        for decimas in range(1, 10):   # dentro del mismo segundo simulado no se recalculan
            sesion.pedir_rutas()
            sesion.comando({'accion': 'paso'})
            esperar(sesion, lambda e: e['t'] >= decimas / 10 - 1e-9)
            time.sleep(0.01)
            self.assertNotIn('rutas', sesion.estado(str(version)))
        sesion.pedir_rutas()
        sesion.comando({'accion': 'paso'})
        esperar(sesion, lambda e: e['t'] >= 1.0)
        self.assertEqual(esperar_rutas(sesion, str(version))['rutas_v'], version + 1)


class PruebasHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sesion = SesionWeb(principal_corto(), 'A', 'S1', 42)
        cls.servidor = crear_servidor(cls.sesion, 0)
        cls.puerto = cls.servidor.server_address[1]
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.sesion.cerrar_todo()

    def pedir(self, metodo, ruta, cuerpo=None, cabeceras=None):
        conexion = http.client.HTTPConnection('127.0.0.1', self.puerto, timeout=5)
        try:
            conexion.request(metodo, ruta, cuerpo, cabeceras or {})
            respuesta = conexion.getresponse()
            respuesta.read()
            return respuesta
        finally:
            conexion.close()

    def test_rutas_por_http_solo_con_parametro(self):
        def leer(ruta):
            conexion = http.client.HTTPConnection('127.0.0.1', self.puerto, timeout=5)
            try:
                conexion.request('GET', ruta)
                return json.loads(conexion.getresponse().read())
            finally:
                conexion.close()

        self.assertNotIn('rutas', leer('/estado'))
        fin = time.monotonic() + 5
        estado = leer('/estado?rutas=1')
        while 'rutas' not in estado and time.monotonic() < fin:
            time.sleep(0.02)
            estado = leer('/estado?rutas=1')
        self.assertIn('rutas', estado)
        self.assertNotIn('rutas', leer(f"/estado?rutas=1&rv={estado['rutas_v']}"))

    def test_solo_escucha_en_localhost(self):
        self.assertEqual(self.servidor.server_address[0], '127.0.0.1')

    def test_estaticos_sin_cache(self):
        for ruta in ('/', '/estilos.css', '/app.js', '/tema.js'):
            respuesta = self.pedir('GET', ruta)
            self.assertEqual(respuesta.status, 200)
            self.assertEqual(respuesta.getheader('Cache-Control'), 'no-store')

    def test_rechazos(self):
        json_ok = {'Content-Type': 'application/json'}
        orden = '{"accion": "pausar"}'
        self.assertEqual(self.pedir('GET', '/estado', cabeceras={'Host': 'evil.example'}).status, 403)
        self.assertEqual(self.pedir('POST', '/control', orden, {
            **json_ok, 'Origin': 'http://evil.example'}).status, 403)
        self.assertEqual(self.pedir('POST', '/control', 'accion=pausar', {
            'Content-Type': 'application/x-www-form-urlencoded'}).status, 415)
        self.assertEqual(self.pedir('POST', '/control', '{mal', json_ok).status, 400)
        for ruta in ('/../main.py', '/..%2fmain.py', '/.git/config', '/main.py'):
            self.assertEqual(self.pedir('GET', ruta).status, 404, ruta)


class PruebasArchivos(unittest.TestCase):
    def test_web_sin_recursos_externos_y_liviana(self):
        archivos = [a for a in (RAIZ / 'web').iterdir() if a.is_file()]
        self.assertLess(sum(a.stat().st_size for a in archivos), 46_000)
        for archivo in archivos:
            texto = archivo.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'https?://|@import|url\(|src="//|href="//', texto), archivo)

    def test_z_capturas_sin_archivos_nuevos(self):
        actuales = {p for p in (RAIZ / 'capturas').rglob('*') if p.is_file()}
        self.assertEqual(actuales - CAPTURAS_INICIALES, set())


if __name__ == '__main__':
    unittest.main()
