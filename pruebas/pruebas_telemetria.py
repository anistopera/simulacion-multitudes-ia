"""Pruebas de telemetría de Flores Choquetopa Nicole: python -m pruebas.pruebas_telemetria."""

import csv
from dataclasses import asdict
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

from modulos.agentes import Agente, MotorAgentes, generar_agentes
from modulos.dbscan_deteccion import detectar_grupos
from modulos.entorno import Entorno
from modulos.optimizacion_pso import costo_J
from modulos.telemetria import COLUMNAS, Telemetria


class PruebasTelemetria(unittest.TestCase):
    def test_distancia_media_al_resto_con_triangulo_conocido(self):
        agentes = [Agente(0, 0, 0), Agente(1, 3, 0), Agente(2, 0, 4)]
        tele = Telemetria()
        tele.registrar(1, agentes)
        np.testing.assert_allclose([f['dist_vecino_medio'] for f in tele.filas], [3.5, 4., 4.5])

    def test_posiciones_normal_vacio_y_un_activo(self):
        tele = Telemetria()
        self.assertEqual(tele.obtener_posiciones_np().shape, (0, 2))
        self.assertEqual(tele.obtener_posiciones_np([]).dtype, np.float64)
        agentes = [Agente(0, 1, 2), Agente(1, 3, 4), Agente(2, 5, 6, activo=False)]
        tele.registrar(1, agentes)
        posiciones = tele.obtener_posiciones_np()
        self.assertEqual(posiciones.shape, (2, 2))
        self.assertEqual(posiciones.dtype, np.float64)
        np.testing.assert_array_equal(posiciones, [[1, 2], [3, 4]])
        tele.registrar(2, [agentes[0]])
        self.assertEqual(tele.filas[-1]['dist_vecino_medio'], 0.0)
        tele.registrar(3, [])
        self.assertEqual(tele.obtener_posiciones_np().shape, (0, 2))
        self.assertEqual(tele.solapamientos_instante, 0)

    def test_posiciones_son_copia_del_muestreo_y_consulta_explicita_actual(self):
        a = Agente(0, 1, 2)
        tele = Telemetria()
        tele.registrar(1, [a])
        salida = tele.obtener_posiciones_np()
        salida[0, 0] = 99
        a.x = 5
        np.testing.assert_array_equal(tele.obtener_posiciones_np(), [[1, 2]])
        np.testing.assert_array_equal(tele.obtener_posiciones_np([a]), [[5, 2]])
        self.assertEqual(len(tele.filas), 1)
        self.assertEqual(tele.filas[0]['x'], 1)

    def test_bloqueo_acumulativo_umbral_estricto_e_intervalo_variable(self):
        a = Agente(0, 1, 1, v_deseada=1.0)
        tele = Telemetria()
        tele.registrar(0.5, [a], dt_muestreo=0.5)
        a.vx, a.vy = 0.3, 0.4  # Rapidez exactamente 50%: no suma bloqueo.
        tele.registrar(1.0, [a], dt_muestreo=0.5)
        a.vx = a.vy = 0.0
        tele.registrar(2.5, [a], dt_muestreo=1.5)
        np.testing.assert_allclose([f['t_bloqueo'] for f in tele.filas], [.5, .5, 2.0])
        self.assertEqual(tele.registros[0]['t_bloqueo'], 2.0)

    def test_solapamientos_pares_sin_duplicar_y_radios_individuales(self):
        agentes = [Agente(0, 1, 1), Agente(1, 1.25, 1),
                   Agente(2, 3, 1, radio=.4), Agente(3, 3.6, 1, radio=.3)]
        tele = Telemetria()
        tele.registrar(1, agentes)
        self.assertEqual(tele.solapamientos_instante, 2)
        tele.registrar(2, agentes)
        self.assertEqual(tele.solapamientos_total, 4)
        tele.registrar(3, [Agente(4, 1, 1), Agente(5, 1.5, 1)])
        self.assertEqual(tele.solapamientos_instante, 0)  # Contacto exacto no cuenta.
        self.assertEqual(tele.solapamientos_total, 4)

    def test_inactivos_y_llegados_no_generan_filas_bloqueo_ni_solapamientos(self):
        a = Agente(0, 1, 1)
        retirado = Agente(1, 1, 1, activo=False)
        llegado = Agente(2, 1, 1, activo=True, llegado=True, tiempo_llegada=.4)
        tele = Telemetria()
        tele.registrar(1, [a, retirado, llegado])
        self.assertEqual([f['id'] for f in tele.filas], [0])
        self.assertEqual(tele.registros[1]['t_bloqueo'], 0)
        self.assertEqual(tele.registros[2]['t_bloqueo'], 0)
        self.assertEqual(tele.solapamientos_total, 0)
        self.assertEqual(tele.obtener_posiciones_np([a, retirado, llegado]).shape, (1, 2))

    def test_objetos_diccionarios_y_no_modificacion_de_agentes(self):
        a, b = Agente(0, 2, 2), asdict(Agente(1, 3, 3))
        antes_a, antes_b = asdict(a), dict(b)
        tele = Telemetria()
        tele.registrar(1, [a, b])
        self.assertEqual(asdict(a), antes_a)
        self.assertEqual(b, antes_b)
        self.assertFalse(hasattr(a, 'tiempo_espera'))
        self.assertEqual(tele.obtener_posiciones_np([a, b]).shape, (2, 2))

    def test_metricas_promedian_poblacion_completa_y_penalizan_no_llegados(self):
        a, b = Agente(0, 1, 1), Agente(1, 2, 1, vx=1.)
        tele = Telemetria()
        tele.registrar(1, [a, b])
        a.activo, a.llegado, a.tiempo_llegada = False, True, 1.25
        tele.registrar(2, [a, b])
        # Aunque el llegado deje de enviarse después, se conserva su tiempo.
        tele.registrar(3, [b])
        m = tele.obtener_metricas_episodio(2, 180)
        self.assertEqual(set(m), {'tiempo_transito', 'tiempo_espera', 'solapamientos',
                                  'tasa_finalizacion', 'llegados', 'activos_final'})
        self.assertAlmostEqual(m['tiempo_transito'], (1.25 + 180) / 2)
        self.assertAlmostEqual(m['tiempo_espera'], .5)
        self.assertEqual(m['tasa_finalizacion'], .5)
        self.assertEqual((m['llegados'], m['activos_final']), (1, 1))
        self.assertTrue(math.isfinite(costo_J(m, m)))
        self.assertEqual(tele.registros[0]['tiempo_transito'], 1.25)
        # Consultar otro horizonte no modifica las llegadas ni los acumuladores.
        self.assertAlmostEqual(tele.obtener_metricas_episodio(2, 20)['tiempo_transito'], 10.625)

    def test_metricas_poblacion_vacia_y_no_observada(self):
        tele = Telemetria()
        self.assertTrue(all(v == 0 for v in tele.obtener_metricas_episodio(0, 0).values()))
        m = tele.obtener_metricas_episodio(40, 180)
        self.assertEqual(m['tiempo_transito'], 180)
        self.assertEqual(m['activos_final'], 40)
        self.assertEqual(m['tasa_finalizacion'], 0)

    def test_csv_encabezado_numeros_y_sin_datos(self):
        tele = Telemetria()
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'subcarpeta' / 'telemetria.csv'
            tele.exportar_csv(str(ruta))
            self.assertEqual(ruta.read_text(encoding='utf-8').strip(), ','.join(COLUMNAS))
            tele.registrar(1, [Agente(7, 2, 3)])
            tele.exportar_csv(str(ruta))
            with ruta.open(encoding='utf-8', newline='') as archivo:
                lector = csv.DictReader(archivo)
                self.assertEqual(lector.fieldnames, list(COLUMNAS))
                filas = list(lector)
            self.assertEqual(len(filas), 1)
            self.assertEqual(int(filas[0]['id']), 7)
            self.assertEqual(float(filas[0]['t_bloqueo']), 1.)
            self.assertTrue(all(math.isfinite(float(v)) for v in filas[0].values()))

    def test_entradas_invalidas_no_alteran_el_muestreo(self):
        tele = Telemetria()
        a = Agente(0, 1, 1)
        tele.registrar(1, [a])
        for t, dt in ((1, 1), (.5, 1), (-1, 1), (float('nan'), 1),
                      (2, 0), (2, -1), (2, float('inf'))):
            with self.assertRaises(ValueError):
                tele.registrar(t, [a], dt)
        for agentes in ([a, a], [dict(asdict(a), x=float('nan'))],
                        [Agente(1, 1, 1, llegado=True)],
                        [Agente(1, 1, 1, llegado=True, tiempo_llegada=3)]):
            with self.assertRaises(ValueError):
                tele.registrar(2, agentes)
        self.assertEqual(len(tele.filas), 1)
        self.assertEqual(tele.registros[0]['t_bloqueo'], 1)
        self.assertEqual(len(tele.registros), 1)
        for total, duracion in ((0, 180), (1, .5), (1, float('nan')), (-1, 180), (True, 180)):
            with self.assertRaises(ValueError):
                tele.obtener_metricas_episodio(total, duracion)

    def test_integracion_motor_dbscan_y_llegadas_reales(self):
        entorno = Entorno()
        agentes = generar_agentes(entorno, cantidad=40, semilla=42)
        motor = MotorAgentes(entorno, agentes)
        tele = Telemetria(entorno)
        for tick in range(400):
            motor.actualizar(.1)
            if (tick + 1) % 10 == 0:
                tele.registrar((tick + 1) / 10, agentes)
                posiciones = tele.obtener_posiciones_np()
                etiquetas, _ = detectar_grupos(posiciones)
                self.assertEqual(etiquetas.shape, (len(motor.agentes_activos),))
        m = tele.obtener_metricas_episodio(40, 40)
        self.assertEqual((m['llegados'], m['activos_final']), (40, 0))
        self.assertAlmostEqual(m['tiempo_transito'], np.mean([a.tiempo_llegada for a in agentes]))
        self.assertEqual(tele.obtener_posiciones_np().shape, (0, 2))


if __name__ == '__main__':
    unittest.main(verbosity=2)
