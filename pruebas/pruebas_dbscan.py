"""Pruebas del modulo de DBSCAN (Daniel Flores Mamani): python -m pruebas.pruebas_dbscan."""

from pathlib import Path
import time
import unittest

import numpy as np
from sklearn.cluster import DBSCAN

from modulos.dbscan_deteccion import (
    TIPO_FRONTERA, TIPO_NUCLEO, TIPO_RUIDO,
    analizar_instante, calidad_agrupamiento, cargar_instantes_csv,
    clasificar_puntos, detectar_grupos, proporcion_ruido,
)

RAIZ = Path(__file__).resolve().parents[1]
CSV_S3 = RAIZ / "capturas" / "datos" / "posiciones_S3_semilla42.csv"


def _instante_real(minimo=100):
    """Instante de S3 con mas agentes; si no hay datos, uno sintetico equivalente."""
    if CSV_S3.exists():
        validos = [X for X in cargar_instantes_csv(CSV_S3) if len(X) >= minimo]
        if validos:
            return max(validos, key=len)
    rng = np.random.default_rng(0)
    return rng.uniform([1, 1], [29, 19], size=(120, 2))


def _dos_grupos_y_ruido():
    rng = np.random.default_rng(0)
    return np.vstack([rng.normal([10, 10], 0.4, (30, 2)),
                      rng.normal([20, 5], 0.4, (30, 2)),
                      [[1.0, 1.0], [28.0, 18.0]]])


class PruebasDBSCAN(unittest.TestCase):
    def test_entrada_vacia(self):
        et, cl = detectar_grupos(np.empty((0, 2)))
        self.assertEqual(len(et), 0)
        self.assertEqual(cl, [])
        et, tipos, cl = clasificar_puntos([])
        self.assertEqual((len(et), len(tipos), cl), (0, 0, []))

    def test_menos_puntos_que_min_samples_es_todo_ruido(self):
        X = np.array([[1.0, 1.0], [1.1, 1.0], [1.2, 1.0]])
        et, tipos, cl = clasificar_puntos(X, 1.2, 5)
        self.assertTrue(np.all(et == -1))
        self.assertTrue(np.all(tipos == TIPO_RUIDO))
        self.assertEqual(cl, [])

    def test_dos_grupos_y_dos_aislados(self):
        et, cl = detectar_grupos(_dos_grupos_y_ruido())
        self.assertEqual(len(cl), 2)
        self.assertEqual(int(np.count_nonzero(et == -1)), 2)
        self.assertEqual([c["tamano"] for c in cl], [30, 30])

    def test_clasificacion_nucleo_frontera_ruido_caso_conocido(self):
        # 5 puntos compactos (nucleo), uno a 1,05 m del ultimo (frontera, solo tiene 3
        # puntos a <= eps contandose a si mismo) y uno lejano (ruido).
        X = np.array([[0.0, 0], [0.1, 0], [0.2, 0], [0.3, 0], [0.4, 0],
                      [1.45, 0], [10.0, 10.0]])
        et, tipos, cl = clasificar_puntos(X, 1.2, 5)
        self.assertTrue(np.all(tipos[:5] == TIPO_NUCLEO))
        self.assertEqual(tipos[5], TIPO_FRONTERA)
        self.assertEqual(tipos[6], TIPO_RUIDO)
        self.assertEqual(et[5], et[0])          # la frontera pertenece al grupo
        self.assertEqual(et[6], -1)
        self.assertEqual((cl[0]["tamano"], cl[0]["n_nucleo"], cl[0]["n_frontera"]), (6, 5, 1))

    def test_coherencia_de_tipos_con_datos_reales(self):
        X = _instante_real()
        et, tipos, cl = clasificar_puntos(X)
        self.assertTrue(np.array_equal(tipos == TIPO_RUIDO, et == -1))
        self.assertTrue(np.all(et[tipos == TIPO_NUCLEO] != -1))
        self.assertEqual(sum(c["tamano"] for c in cl) + int(np.count_nonzero(et == -1)), len(X))
        for c in cl:
            self.assertEqual(c["n_nucleo"] + c["n_frontera"], c["tamano"])
            self.assertGreaterEqual(c["n_nucleo"], 5)

    def test_nucleo_cumple_la_definicion_con_vecinos_reales(self):
        X = _instante_real()
        _, tipos, _ = clasificar_puntos(X, 1.2, 5)
        dist = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
        vecinos = (dist <= 1.2).sum(axis=1)       # incluye al propio punto
        self.assertTrue(np.array_equal(tipos == TIPO_NUCLEO, vecinos >= 5))

    def test_compatibilidad_del_contrato_original(self):
        X = _dos_grupos_y_ruido()
        et, cl = detectar_grupos(X, 1.2, 5)
        for c in cl:
            for clave in ("id", "tamano", "centro_x", "centro_y"):
                self.assertIn(clave, c)
        self.assertEqual([c["tamano"] for c in cl], sorted([c["tamano"] for c in cl], reverse=True))
        referencia = DBSCAN(eps=1.2, min_samples=5).fit_predict(X)  # sin kd_tree explicito
        self.assertTrue(np.array_equal(et == -1, referencia == -1))
        self.assertEqual(len(set(et) - {-1}), len(set(referencia) - {-1}))

    def test_los_algoritmos_de_vecinos_dan_el_mismo_ruido_y_numero_de_grupos(self):
        X = _instante_real()
        base_et, base_cl = detectar_grupos(X, algoritmo="kd_tree")
        for alg in ("ball_tree", "brute"):
            et, cl = detectar_grupos(X, algoritmo=alg)
            self.assertTrue(np.array_equal(et == -1, base_et == -1), alg)
            self.assertEqual(len(cl), len(base_cl), alg)

    def test_metricas_solo_con_dos_grupos_y_sin_ruido(self):
        X = _dos_grupos_y_ruido()
        et, _ = detectar_grupos(X)
        sil, dbi = calidad_agrupamiento(X, et)
        self.assertTrue(-1.0 <= sil <= 1.0)
        self.assertGreaterEqual(dbi, 0.0)
        self.assertGreater(sil, 0.5)               # grupos bien separados
        un_grupo = np.random.default_rng(1).normal([5, 5], 0.3, (20, 2))
        e1, _ = detectar_grupos(un_grupo)
        self.assertEqual(calidad_agrupamiento(un_grupo, e1), (None, None))
        self.assertEqual(calidad_agrupamiento(np.empty((0, 2)), []), (None, None))

    def test_analizar_instante_resume_todo(self):
        X = _dos_grupos_y_ruido()
        r = analizar_instante(X)
        self.assertEqual(r["n_agentes"], 62)
        self.assertEqual(r["n_nucleo"] + r["n_frontera"] + r["n_ruido"], 62)
        self.assertEqual(r["n_ruido"], 2)
        self.assertAlmostEqual(r["pct_ruido"], 100 * 2 / 62, places=6)
        self.assertIsNotNone(r["silhouette"])
        sin = analizar_instante(X, con_metricas=False)
        self.assertIsNone(sin["silhouette"])
        self.assertIsNone(sin["davies_bouldin"])

    def test_es_determinista(self):
        X = _instante_real()
        a = clasificar_puntos(X)
        b = clasificar_puntos(X)
        self.assertTrue(np.array_equal(a[0], b[0]))
        self.assertTrue(np.array_equal(a[1], b[1]))

    def test_tiempo_menor_a_2_ms_con_40_80_y_120_agentes(self):
        base = _instante_real()
        rng = np.random.default_rng(3)
        for n in (40, 80, 120):
            X = base[rng.choice(len(base), size=min(n, len(base)), replace=False)]
            for _ in range(20):                     # calentamiento
                detectar_grupos(X)
            muestras = []
            for _ in range(200):
                t0 = time.perf_counter()
                detectar_grupos(X)
                muestras.append((time.perf_counter() - t0) * 1000)
            mediana = float(np.median(muestras))
            self.assertLess(mediana, 2.0, f"n={n}: mediana {mediana:.3f} ms")

    def test_proporcion_ruido(self):
        self.assertEqual(proporcion_ruido([]), 0.0)
        self.assertEqual(proporcion_ruido([-1, -1, 0, 0]), 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
