"""Mide el tiempo de DBSCAN por llamada con 40, 80 y 120 agentes (datos reales).

Uso: python -m scripts_analisis.benchmark_dbscan
Escribe capturas/benchmark_dbscan.csv y muestra una tabla en consola.
"""

import csv
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REPETICIONES = 300
ALGORITMOS = ("kd_tree", "ball_tree", "brute", "auto")


def _mediciones(f, repeticiones):
    import numpy as np
    for _ in range(30):                        # calentamiento
        f()
    t = []
    for _ in range(repeticiones):
        t0 = time.perf_counter()
        f()
        t.append((time.perf_counter() - t0) * 1000)
    t = np.array(t)
    return float(np.median(t)), float(np.percentile(t, 95)), float(t.max())


def main():
    from modulos.dbscan_deteccion import (analizar_instante, cargar_instantes_csv,
                                          detectar_grupos, EPS_DEFECTO, MIN_SAMPLES_DEFECTO)
    filas = []
    print(f"{'esc':4s} {'n':>4s} {'algoritmo':10s} {'mediana ms':>11s} {'p95 ms':>8s} {'max ms':>8s}")
    for esc in ("S1", "S2", "S3"):
        instantes = cargar_instantes_csv(RAIZ / "capturas" / "datos" / f"posiciones_{esc}_semilla42.csv")
        X = max(instantes, key=len)
        for alg in ALGORITMOS:
            med, p95, mx = _mediciones(lambda: detectar_grupos(X, EPS_DEFECTO, MIN_SAMPLES_DEFECTO, alg),
                                       REPETICIONES)
            filas.append({"escenario": esc, "agentes": len(X), "algoritmo": alg, "mediana_ms": round(med, 3),
                          "p95_ms": round(p95, 3), "max_ms": round(mx, 3), "cumple_2ms": med < 2.0})
            print(f"{esc:4s} {len(X):4d} {alg:10s} {med:11.3f} {p95:8.3f} {mx:8.3f}")
        # coste del analisis completo (DBSCAN + clasificacion + Silhouette + Davies-Bouldin)
        med, p95, mx = _mediciones(lambda: analizar_instante(X), 100)
        filas.append({"escenario": esc, "agentes": len(X), "algoritmo": "analisis_completo", "mediana_ms": round(med, 3),
                      "p95_ms": round(p95, 3), "max_ms": round(mx, 3), "cumple_2ms": med < 2.0})
        print(f"{esc:4s} {len(X):4d} {'completo':10s} {med:11.3f} {p95:8.3f} {mx:8.3f}")
    ruta = RAIZ / "capturas" / "benchmark_dbscan.csv"
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
    print("Guardado en", ruta)


if __name__ == "__main__":
    main()
