"""Verifica relojes, cierre anticipado, navegación y agregación experimental."""

import contextlib
import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
