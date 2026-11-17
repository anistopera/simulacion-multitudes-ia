"""Pruebas del motor de Sthaicy: python -m pruebas.pruebas_agentes."""
import math
import unittest

import numpy as np

from modulos.agentes import Agente, MotorAgentes, generar_agentes, posicion_valida
from modulos.entorno import Entorno
from modulos.diagnostico import DiagnosticoCongestion
from modulos.navegacion_astar import NavegadorAdaptativo


class PruebasAgentes(unittest.TestCase):
    def setUp(self):
        self.entorno = Entorno()

    def test_interfaz_wendy_y_rutas_independientes(self):
        a, b = Agente(0, 2, 3), Agente(1, 4, 5)
        a.vx, a.vy = 0.3, 0.4
        self.assertAlmostEqual(a.velocidad, 0.5)
        self.assertEqual(a.radio, 0.25)
        a.ruta.append((3, 3))
        self.assertEqual(b.ruta, [])
        self.assertTrue(a.activo)
        self.assertFalse(a.llegado)

    def test_generacion_s1_s2_s3_reproducible_y_sin_solapamientos(self):
        for n in (40, 80, 120):
            agentes = generar_agentes(self.entorno, n, semilla=7)
            repetidos = generar_agentes(self.entorno, n, semilla=7)
            self.assertEqual(agentes, repetidos)
            self.assertEqual(len({a.id for a in agentes}), n)
            self.assertNotEqual(agentes, generar_agentes(self.entorno, n, semilla=8))
            for i, a in enumerate(agentes):
                self.assertTrue(posicion_valida(self.entorno, a.x, a.y, a.radio))
                self.assertLess(a.x, 15)
                self.assertTrue(0.9 <= a.v_deseada <= 1.5)
                for b in agentes[:i]:
                    self.assertGreaterEqual(math.hypot(a.x-b.x, a.y-b.y), a.radio+b.radio)
        self.assertEqual(generar_agentes(self.entorno, 0), [])

    def test_errores_de_entrada(self):
        for kwargs in ({'radio': 0}, {'x': float('nan')}, {'v_deseada': -1}):
            datos = dict(id=0, x=1, y=11)
            datos.update(kwargs)
            with self.assertRaises(ValueError):
                Agente(**datos)
        for cantidad in (-1, 2.5, True, 100000):
            with self.assertRaises(ValueError):
                generar_agentes(self.entorno, cantidad)
        with self.assertRaises(ValueError):
            MotorAgentes(self.entorno, [Agente(0, 1, 11), Agente(0, 2, 11)])
        with self.assertRaises(ValueError):
            MotorAgentes(self.entorno, [Agente(0, 1, 11), Agente(1, 1.1, 11)])
        motor = MotorAgentes(self.entorno, [])
        for dt in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                motor.actualizar(dt)

    def test_disco_completo_y_obstaculo_configurable(self):
        self.assertTrue(self.entorno.es_transitable(14.9, 8))
        self.assertFalse(posicion_valida(self.entorno, 14.9, 8))
        self.assertFalse(posicion_valida(self.entorno, 0.1, 11))
        self.entorno.agregar_obstaculo(5, 5)
        self.assertFalse(posicion_valida(self.entorno, 4.9, 5.5))

    def test_aceleracion_velocidad_e_integracion_en_espacio_libre(self):
        a = Agente(0, 3.5, 11.5, destino=(10.5, 11.5))
        motor = MotorAgentes(self.entorno, [a], ks=0, kr=0)
        for _ in range(30):
            antes = np.array([a.x, a.y])
            v0 = np.array([a.vx, a.vy])
            motor.actualizar(0.1)
            v1 = np.array([a.vx, a.vy])
            self.assertLessEqual(np.linalg.norm(v1-v0), motor.aceleracion_max*0.1+1e-10)
            self.assertLessEqual(a.velocidad, motor.velocidad_max+1e-10)
            np.testing.assert_allclose([a.x, a.y], antes+v1*0.1, atol=1e-12)
        self.assertGreater(a.x, 6)

    def test_separacion_actua_sin_atraccion(self):
        agentes = [Agente(0, 3, 3), Agente(1, 3.55, 3)]
        motor = MotorAgentes(self.entorno, agentes, ko=0, kr=0)
        motor.actualizar()
        self.assertLess(agentes[0].vx, 0)
        self.assertGreater(agentes[1].vx, 0)

    def test_repulsion_de_pared_actua_sin_atraccion(self):
        a = Agente(0, 14.6, 8)
        motor = MotorAgentes(self.entorno, [a], ko=0, ks=0)
        motor.actualizar()
        self.assertLess(a.vx, 0)

    def test_contactos_no_cruzan_entre_agentes(self):
        agentes = [Agente(0, 3, 3, vx=1.5, destino=(5, 3), ruta=[(5, 3)]),
                   Agente(1, 3.51, 3, vx=-1.5, destino=(1, 3), ruta=[(1, 3)])]
        motor = MotorAgentes(self.entorno, agentes, ks=0, kr=0)
        motor.actualizar()
        self.assertGreaterEqual(agentes[1].x-agentes[0].x, 0.5-1e-10)
        self.assertEqual(agentes[0].vx, 0)
        self.assertEqual(agentes[1].vx, 0)

    def test_no_atraviesa_pared_con_dt_grande(self):
        a = Agente(0, 14.5, 8.5, vx=1.5, destino=(17.5, 8.5), ruta=[(17.5, 8.5)])
        motor = MotorAgentes(self.entorno, [a], ks=0, kr=0)
        motor.actualizar(2.0)
        self.assertLessEqual(a.x, 14.75)
        self.assertTrue(posicion_valida(self.entorno, a.x, a.y))
        self.assertAlmostEqual(motor.tiempo, 2)

    def test_barrido_respeta_esquinas_y_radio(self):
        motor = MotorAgentes(self.entorno, [])
        rect = np.array([[5., 5., 6., 6.]])
        # Disco junto a una esquina, fuera del rectángulo expandido redondeado.
        self.assertTrue(motor._trayectoria_libre(np.array([4.8, 4.8]),
                                               np.array([4.7, 4.7]), 0.25, rect))
        self.assertFalse(motor._trayectoria_libre(np.array([4., 5.5]),
                                                np.array([7., 5.5]), 0.25, rect))

    def test_llegada_usando_solo_ruta_alternativa(self):
        for y in (10, 11):
            self.entorno.agregar_obstaculo(15, y)
        a = Agente(0, 1, 11)
        motor = MotorAgentes(self.entorno, [a])
        for _ in range(600):
            motor.actualizar()
            self.assertTrue(posicion_valida(self.entorno, a.x, a.y))
            if a.llegado:
                break
        self.assertTrue(a.llegado)

    def test_llegada_al_destino_real_y_estabilidad(self):
        a = Agente(0, 1, 11)
        agentes = [a]
        motor = MotorAgentes(self.entorno, agentes)
        for _ in range(500):
            motor.actualizar()
            if a.llegado:
                break
        self.assertTrue(a.llegado)
        self.assertFalse(a.activo)
        self.assertLessEqual(math.hypot(a.x-29, a.y-11), motor.tolerancia_llegada)
        self.assertIs(motor.agentes, agentes)
        self.assertIs(motor.agentes[0], a)
        final = (a.x, a.y, a.tiempo_llegada)
        motor.actualizar()
        self.assertEqual((a.x, a.y, a.tiempo_llegada), final)
        self.assertEqual(motor.agentes_activos, [])

    def test_s1_no_se_bloquea_artificialmente_en_la_salida(self):
        agentes = generar_agentes(self.entorno, 40, semilla=42)
        motor = MotorAgentes(self.entorno, agentes)
        for _ in range(600):
            motor.actualizar()
        self.assertTrue(all(a.llegado for a in agentes))

    def test_compatibilidad_diagnostico_y_reemplazo_ruta_keyla(self):
        agentes = generar_agentes(self.entorno, 40)
        motor = MotorAgentes(self.entorno, agentes)
        diagnostico = DiagnosticoCongestion(entorno=self.entorno)
        for _ in range(10):
            motor.actualizar()
        estados, D = diagnostico.actualizar(motor.agentes_activos, dt=1)
        self.assertEqual(D.shape, (10, 15))
        self.assertEqual(estados.shape, (10, 15))
        self.assertEqual(diagnostico.conteo_agentes.sum(), len(motor.agentes_activos))
        nav = NavegadorAdaptativo(self.entorno, 'B')
        a = agentes[0]
        nav.asignar_ruta_inicial(a, t=motor.tiempo, D=D)
        nueva = a.ruta
        motor.actualizar()
        self.assertIs(a.ruta, nueva)
        self.assertTrue(all(posicion_valida(self.entorno, a.x, a.y) for a in agentes))

    def test_120_agentes_durante_diez_segundos(self):
        agentes = generar_agentes(self.entorno, 120)
        motor = MotorAgentes(self.entorno, agentes)
        inicial = np.array([[a.x, a.y] for a in agentes])
        for _ in range(100):
            motor.actualizar()
            activos = motor.agentes_activos
            for i, a in enumerate(activos):
                self.assertTrue(posicion_valida(self.entorno, a.x, a.y))
                self.assertLessEqual(a.velocidad, motor.velocidad_max+1e-10)
                for b in activos[:i]:
                    self.assertGreaterEqual(math.hypot(a.x-b.x, a.y-b.y), a.radio+b.radio-1e-9)
        self.assertGreater(np.mean([a.x for a in agentes]), inicial[:, 0].mean()+1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
