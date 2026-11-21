
# -*- coding: utf-8 -*-
"""
Pruebas unitarias del algoritmo PSO.
Responsable del modulo: Orellana Castro Keyla.
"""

import unittest
import numpy as np

from modulos.optimizacion_pso import (
    LIMITES,
    costo_J,
    pso,
)


class PruebasPSO(unittest.TestCase):

    def test_01_limites_validos(self):
        """Verifica los limites de alpha, ks y kr."""
        self.assertEqual(LIMITES["alpha"], (0.0, 5.0))
        self.assertEqual(LIMITES["ks"], (0.5, 2.0))
        self.assertEqual(LIMITES["kr"], (0.5, 3.0))

    def test_02_costo_J(self):
        """Verifica el calculo de la funcion de costo."""
        base = {
            "tiempo_transito": 100,
            "tiempo_espera": 50,
            "solapamientos": 10,
        }

        metricas = {
            "tiempo_transito": 50,
            "tiempo_espera": 25,
            "solapamientos": 5,
            "tasa_finalizacion": 1.0,
        }

        resultado = costo_J(metricas, base)
        self.assertAlmostEqual(resultado, 0.50)

    def test_03_penalizacion_no_llegados(self):
        """Comprueba la penalizacion por agentes que no llegan."""
        base = {
            "tiempo_transito": 100,
            "tiempo_espera": 50,
            "solapamientos": 10,
        }

        metricas = {
            "tiempo_transito": 100,
            "tiempo_espera": 50,
            "solapamientos": 10,
            "tasa_finalizacion": 0.5,
        }

        self.assertAlmostEqual(costo_J(metricas, base), 1.5)

    def test_04_parametros_dentro_limites(self):
        """Verifica que PSO respete los limites establecidos."""
        def evaluar(theta):
            return float(np.sum(theta ** 2))

        theta, mejor_J, historial = pso(
            evaluar,
            n_particulas=5,
            iteraciones=5,
            semilla=42,
        )

        for valor, (minimo, maximo) in zip(
            theta, LIMITES.values()
        ):
            self.assertGreaterEqual(valor, minimo)
            self.assertLessEqual(valor, maximo)

        self.assertTrue(np.isfinite(mejor_J))

    def test_05_reproducibilidad(self):
        """La misma semilla debe generar el mismo resultado."""
        def evaluar(theta):
            return float(np.sum(theta ** 2))

        resultado1 = pso(
            evaluar, n_particulas=5,
            iteraciones=5, semilla=42
        )

        resultado2 = pso(
            evaluar, n_particulas=5,
            iteraciones=5, semilla=42
        )

        np.testing.assert_array_equal(
            resultado1[0], resultado2[0]
        )
        self.assertEqual(resultado1[1], resultado2[1])
        self.assertEqual(resultado1[2], resultado2[2])

    def test_06_historial_convergencia(self):
        """El mejor costo global no debe aumentar."""
        def evaluar(theta):
            return float(np.sum(theta ** 2))

        _, _, historial = pso(
            evaluar,
            n_particulas=5,
            iteraciones=10,
            semilla=42,
        )

        self.assertEqual(len(historial), 11)

        for anterior, siguiente in zip(
            historial, historial[1:]
        ):
            self.assertLessEqual(siguiente, anterior)

    def test_07_resultado_optimizacion(self):
        """Verifica que PSO devuelva una solucion valida."""
        objetivo = np.array([1.5, 1.0, 2.0])

        def evaluar(theta):
            return float(np.sum((theta - objetivo) ** 2))

        theta, mejor_J, historial = pso(
            evaluar,
            n_particulas=10,
            iteraciones=15,
            semilla=2026,
        )

        self.assertEqual(len(theta), 3)
        self.assertTrue(np.all(np.isfinite(theta)))
        self.assertAlmostEqual(mejor_J, evaluar(theta))
        self.assertLessEqual(mejor_J, historial[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
