"""Verifica relojes, cierre anticipado, navegación y agregación experimental."""

import contextlib
import csv
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

import main
from modulos.telemetria import Telemetria


class PruebasIntegracion(unittest.TestCase):
    def test_relojes_fisica_analisis_y_cierre_parcial(self):
        llamadas = []

        class RegistroObservado(Telemetria):
            def registrar(self, t, agentes, dt_muestreo=1.0):
                llamadas.append((t, dt_muestreo))
                return super().registrar(t, agentes, dt_muestreo)

        for modo in ('A', 'B'):
            llamadas.clear()
            with tempfile.TemporaryDirectory() as carpeta:
                with patch('main.Telemetria', RegistroObservado), \
                     patch('main.detectar_grupos', wraps=main.detectar_grupos) as dbscan, \
                     patch.object(main.NavegadorAdaptativo, 'actualizar_todos', return_value=0) as nav:
                    r = main.ejecutar_episodio(40, modo, 42, duracion=1.3, carpeta_salida=carpeta)
                self.assertEqual(r['ticks'], 13)
                self.assertEqual(r['muestras_analisis'], 1)
                self.assertEqual(dbscan.call_count, 1)
                self.assertEqual(nav.call_count, int(modo == 'B'))
                np.testing.assert_allclose(llamadas, [[1., 1.], [1.3, .3]])
                with (Path(carpeta) / r['archivo_analisis']).open(encoding='utf-8') as f:
                    fila = next(csv.DictReader(f))
                self.assertEqual(int(fila['activos']), 40)
                self.assertEqual(r['activos_final'] + r['llegados'], 40)

    def test_ultimas_llegadas_entre_muestras_no_se_pierden(self):
        class MotorConLlegadaTemprana:
            def __init__(self, entorno, agentes):
                self.agentes = agentes
                self.tiempo = 0.

            def actualizar(self, dt):
                self.tiempo += dt
                if self.tiempo >= .3:
                    for a in self.agentes:
                        a.activo, a.llegado, a.tiempo_llegada = False, True, self.tiempo
                    return []
                return self.agentes

        with tempfile.TemporaryDirectory() as carpeta, patch('main.MotorAgentes', MotorConLlegadaTemprana):
            r = main.ejecutar_episodio(40, duracion=180, carpeta_salida=carpeta)
            self.assertEqual(r['ticks'], 3)
            self.assertEqual(r['llegados'], 40)
            self.assertEqual(r['activos_final'], 0)
            self.assertEqual(r['tasa_finalizacion_pct'], 100)
            self.assertAlmostEqual(r['tiempo_transito'], .3)
            self.assertEqual(r['filas_telemetria'], 0)
            self.assertEqual(r['muestras_analisis'], 0)

    def test_cierre_real_y_archivos_reproducibles(self):
        with tempfile.TemporaryDirectory() as carpeta:
            r = main.ejecutar_episodio(40, 'A', 42, duracion=40, carpeta_salida=carpeta)
            self.assertEqual(r['llegados'], 40)
            self.assertEqual(r['activos_final'], 0)
            self.assertLess(r['duracion_simulada_s'], 40)
            self.assertEqual(r['cambios_ruta'], 0)
            self.assertEqual(r['recalculos_astar'], 0)
            with (Path(carpeta) / r['archivo_telemetria']).open(encoding='utf-8') as f:
                filas = list(csv.DictReader(f))
            self.assertEqual(len(filas), r['filas_telemetria'])
            self.assertTrue(all(float(f['t']) <= r['duracion_simulada_s'] for f in filas))

    def test_resumen_promedia_totales_y_maximos_por_corrida(self):
        filas = []
        for valor in (2, 4, 6):
            filas.append({'escenario': 'S1', 'modo': 'A',
                          **{k: valor for k in main.METRICAS_COMPARADAS}})
        resumen = main.resumir_resultados(filas)
        self.assertEqual(len(resumen), 1)
        r = resumen[0]
        self.assertEqual(r['n_semillas'], 3)
        self.assertEqual(r['solapamientos'], 4)
        self.assertEqual(r['solapamientos_suma'], 12)
        self.assertEqual(r['celdas_criticas_max'], 4)
        self.assertEqual(r['celdas_criticas_pico'], 6)
        self.assertAlmostEqual(r['tiempo_transito_std'], np.std([2, 4, 6]))

    def test_cli_ayuda_y_opciones_incompatibles(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida), patch('main.ejecutar_episodio') as episodio:
            main.main([])
        self.assertIn('--experimentos', salida.getvalue())
        episodio.assert_not_called()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main.main(['--experimentos', '--modo', 'B'])
        self.assertEqual(error.exception.code, 2)

    def test_cli_individual_respeta_modo_carga_y_semilla(self):
        resultado = {'escenario': 'S3', 'llegados': 120}
        with contextlib.redirect_stdout(io.StringIO()), \
             patch('main.ejecutar_episodio', return_value=resultado) as episodio, \
             patch('main.guardar_csv') as guardar:
            main.main(['--modo', 'B', '--agentes', '120', '--semilla', '42'])
        episodio.assert_called_once_with(120, 'B', 42)
        guardar.assert_called_once_with(main.CAPTURAS / 'resultado_S3_B_semilla42.csv', [resultado])

    def test_visualizador_recibe_densidad_y_eventos_cada_tick(self):
        vista, reloj = Mock(), Mock()
        vista.procesar_eventos.return_value = True
        diagnosticos = []
        clase_diagnostico = main.DiagnosticoCongestion

        def crear_diagnostico(**kwargs):
            diagnosticos.append(clase_diagnostico(**kwargs))
            return diagnosticos[-1]

        with tempfile.TemporaryDirectory() as carpeta, \
             patch('main._crear_visualizacion', return_value=(vista, reloj)), \
             patch('main.DiagnosticoCongestion', side_effect=crear_diagnostico):
            r = main.ejecutar_episodio(40, 'B', 42, duracion=1.3,
                                       carpeta_salida=carpeta, visualizar=True)
        self.assertEqual(vista.procesar_eventos.call_count, 13)
        self.assertEqual(vista.dibujar.call_count, 13)
        self.assertEqual(reloj.tick.call_count, 13)
        self.assertEqual(r['muestras_analisis'], 1)
        for llamada in vista.dibujar.call_args_list:
            self.assertIs(llamada.kwargs['densidad'], diagnosticos[0].densidad)
            self.assertIsNot(llamada.kwargs['densidad'], diagnosticos[0].matriz_D)
            self.assertEqual(llamada.kwargs['llegados'], 0)
            self.assertTrue(all(a.activo and not a.llegado for a in llamada.args[0]))
        vista.cerrar.assert_called_once_with()

    def test_cierre_visual_inmediato_y_entre_muestras(self):
        for pasos in (0, 3):
            with self.subTest(pasos=pasos):
                vista, reloj = Mock(), Mock()
                vista.procesar_eventos.side_effect = [True] * pasos + [False]
                with tempfile.TemporaryDirectory() as carpeta, \
                     patch('main._crear_visualizacion', return_value=(vista, reloj)):
                    r = main.ejecutar_episodio(40, 'B', 42, carpeta_salida=carpeta,
                                               visualizar=True)
                    self.assertTrue((Path(carpeta) / r['archivo_telemetria']).exists())
                    self.assertFalse((Path(carpeta) / 'experimentos/S1_B_semilla42_telemetria.csv').exists())
                self.assertTrue(r['interrumpido'])
                self.assertEqual(r['ticks'], pasos)
                self.assertAlmostEqual(r['duracion_simulada_s'], pasos * .1)
                self.assertAlmostEqual(r['tiempo_transito'], pasos * .1)
                self.assertEqual(vista.dibujar.call_count, pasos)
                vista.cerrar.assert_called_once_with()

    def test_cierra_visualizador_si_falla_el_dibujo(self):
        vista = Mock()
        vista.procesar_eventos.return_value = True
        vista.dibujar.side_effect = RuntimeError('fallo de dibujo de prueba')
        with tempfile.TemporaryDirectory() as carpeta, \
             patch('main._crear_visualizacion', return_value=(vista, Mock())):
            with self.assertRaisesRegex(RuntimeError, 'fallo de dibujo'):
                main.ejecutar_episodio(40, carpeta_salida=carpeta, visualizar=True)
        vista.cerrar.assert_called_once_with()

    def test_main_con_pygame_real_dummy_conserva_las_metricas(self):
        creador_real = main._crear_visualizacion
        dibujos = []

        def crear_sin_espera(*args):
            vista, _ = creador_real(*args)
            vista.dibujar = Mock(wraps=vista.dibujar)
            dibujos.append(vista.dibujar)
            return vista, Mock()

        with tempfile.TemporaryDirectory() as carpeta, \
             patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy', 'PYGAME_HIDE_SUPPORT_PROMPT': '1'}):
            sin_vista = main.ejecutar_episodio(40, 'B', 42, duracion=1,
                                              carpeta_salida=Path(carpeta) / 'sin_vista')
            with patch('main._crear_visualizacion', side_effect=crear_sin_espera):
                con_vista = main.ejecutar_episodio(40, 'B', 42, duracion=1,
                                                  carpeta_salida=Path(carpeta) / 'con_vista',
                                                  visualizar=True)
        for clave in ('ticks', 'tiempo_transito', 'tiempo_espera', 'solapamientos',
                      'llegados', 'activos_final', 'celdas_criticas_max', 'cambios_ruta'):
            self.assertEqual(con_vista[clave], sin_vista[clave])
        self.assertEqual(dibujos[0].call_count, 10)
        import pygame
        self.assertFalse(pygame.display.get_init())


if __name__ == '__main__':
    unittest.main(verbosity=2)
