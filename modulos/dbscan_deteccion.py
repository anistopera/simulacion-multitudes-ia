"""
Modulo 5.4 - Deteccion de grupos con DBSCAN (Grupo 13, IA).

Entrada  : arreglo NumPy de forma (n, 2) con [x, y] en metros (lo entrega Telemetria).
Salida   : etiquetas por agente (-1 = ruido) y resumen de cada cluster (tamano y centro).
Uso      : se llama cada 1 s de simulacion.
"""
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score

EPS_DEFECTO = 1.2        # m
MIN_SAMPLES_DEFECTO = 5  # agentes


def detectar_grupos(posiciones, eps=EPS_DEFECTO, min_samples=MIN_SAMPLES_DEFECTO):
    """Aplica DBSCAN a las posiciones [x, y] de un instante.

    Devuelve (etiquetas, clusters):
      etiquetas : np.ndarray (n,) con la etiqueta de cada agente, -1 = ruido.
      clusters  : lista de dicts {id, tamano, centro_x, centro_y}, ordenada por tamano.
    """
    X = np.asarray(posiciones, dtype=float).reshape(-1, 2)
    if len(X) == 0:
        return np.array([], dtype=int), []

    etiquetas = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)

    clusters = []
    for k in sorted(set(etiquetas) - {-1}):
        miembros = X[etiquetas == k]
        centro = miembros.mean(axis=0)
        clusters.append({
            "id": int(k),
            "tamano": int(len(miembros)),
            "centro_x": float(centro[0]),
            "centro_y": float(centro[1]),
        })
    clusters.sort(key=lambda c: c["tamano"], reverse=True)
    return etiquetas, clusters


def calidad_agrupamiento(posiciones, etiquetas):
    """Silhouette y Davies-Bouldin, solo si hay al menos 2 clusters.

    El ruido (-1) se excluye del calculo porque no es un grupo.
    Devuelve (silhouette, davies_bouldin); (None, None) si no se pueden calcular.
    """
    X = np.asarray(posiciones, dtype=float).reshape(-1, 2)
    etiquetas = np.asarray(etiquetas)
    mascara = etiquetas != -1
    if mascara.sum() < 3 or len(set(etiquetas[mascara])) < 2:
        return None, None
    Xc, lc = X[mascara], etiquetas[mascara]
    return float(silhouette_score(Xc, lc)), float(davies_bouldin_score(Xc, lc))


def proporcion_ruido(etiquetas):
    etiquetas = np.asarray(etiquetas)
    return float(np.mean(etiquetas == -1)) if len(etiquetas) else 0.0


def calibrar(instantes, eps_lista=(0.8, 1.0, 1.2, 1.5, 2.0), minpts_lista=range(3, 9)):
    """Prueba todas las combinaciones (eps, min_samples) sobre una lista de instantes.

    instantes : lista de arreglos (n, 2). Devuelve lista de filas (dict) con promedios.
    """
    filas = []
    for eps in eps_lista:
        for mp in minpts_lista:
            n_cl, ruido, sil, dbi = [], [], [], []
            for X in instantes:
                et, cl = detectar_grupos(X, eps, mp)
                n_cl.append(len(cl))
                ruido.append(proporcion_ruido(et))
                s, d = calidad_agrupamiento(X, et)
                if s is not None:
                    sil.append(s)
                    dbi.append(d)
            filas.append({
                "eps": eps,
                "min_samples": mp,
                "clusters_prom": float(np.mean(n_cl)),
                "ruido_pct": 100 * float(np.mean(ruido)),
                "silhouette": float(np.mean(sil)) if sil else None,
                "davies_bouldin": float(np.mean(dbi)) if dbi else None,
                "instantes_con_2_clusters": len(sil),
                "instantes": len(instantes),
            })
    return filas


def cargar_instantes_csv(ruta):
    """Lee un CSV con columnas t, x, y (el resto se ignora, p. ej. id, vx, vy) y devuelve
    una lista de arreglos (n, 2), uno por cada instante t ordenado. Sirve tanto para el
    CSV de telemetria acordado (t, id, x, y, vx, vy, ...) como para el generado por
    generar_posiciones_dbscan.py."""
    import csv
    por_t = {}
    with open(ruta, newline="", encoding="utf-8") as fh:
        for fila in csv.DictReader(fh):
            por_t.setdefault(float(fila["t"]), []).append((float(fila["x"]), float(fila["y"])))
    return [np.array(por_t[t]) for t in sorted(por_t)]
