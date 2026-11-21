"""
Modulo 5.4 - Deteccion de grupos con DBSCAN (Grupo 13, IA).

Entrada  : arreglo NumPy de forma (n, 2) con [x, y] en metros (lo entrega Telemetria).
Salida   : etiquetas por agente (-1 = ruido), tipo de cada punto (nucleo / frontera /
           ruido) y resumen de cada cluster (tamano y centro).
Uso      : se llama cada 1 s de simulacion.

Version 3:
  * La busqueda de vecinos usa un kd_tree (algoritmo configurable).
  * Clasificacion explicita de puntos en NUCLEO, FRONTERA y RUIDO.
  * Silhouette y Davies-Bouldin solo con >= 2 grupos validos (el ruido se excluye).

Contrato retrocompatible: detectar_grupos() conserva su firma y su retorno
(etiquetas, clusters). Las claves nuevas de cada cluster son adicionales.
"""
import time

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score

EPS_DEFECTO = 1.2        # m
MIN_SAMPLES_DEFECTO = 5  # agentes (sklearn cuenta al propio punto)
ALGORITMO_DEFECTO = "kd_tree"

# Tipos de punto segun DBSCAN
TIPO_RUIDO = 0
TIPO_FRONTERA = 1
TIPO_NUCLEO = 2
NOMBRES_TIPO = {TIPO_RUIDO: "ruido", TIPO_FRONTERA: "frontera", TIPO_NUCLEO: "nucleo"}


def _como_matriz(posiciones):
    return np.asarray(posiciones, dtype=float).reshape(-1, 2)


def _ajustar(X, eps, min_samples, algoritmo):
    """Ejecuta DBSCAN una sola vez. Devuelve (etiquetas, es_nucleo)."""
    n = len(X)
    if n == 0:
        return np.array([], dtype=int), np.array([], dtype=bool)
    if n < min_samples:
        # Con menos puntos que min_samples nadie puede ser nucleo: todo es ruido.
        return np.full(n, -1, dtype=int), np.zeros(n, dtype=bool)
    modelo = DBSCAN(eps=eps, min_samples=min_samples, algorithm=algoritmo).fit(X)
    es_nucleo = np.zeros(n, dtype=bool)
    es_nucleo[modelo.core_sample_indices_] = True
    return modelo.labels_, es_nucleo


def _tipos(etiquetas, es_nucleo):
    tipos = np.full(len(etiquetas), TIPO_FRONTERA, dtype=np.int8)
    tipos[etiquetas == -1] = TIPO_RUIDO
    tipos[es_nucleo] = TIPO_NUCLEO
    return tipos


def _resumir_clusters(X, etiquetas, es_nucleo):
    clusters = []
    for k in sorted(set(etiquetas.tolist()) - {-1}):
        mascara = etiquetas == k
        centro = X[mascara].mean(axis=0)
        n_nucleo = int(np.count_nonzero(mascara & es_nucleo))
        clusters.append({
            "id": int(k),
            "tamano": int(mascara.sum()),
            "centro_x": float(centro[0]),
            "centro_y": float(centro[1]),
            "n_nucleo": n_nucleo,
            "n_frontera": int(mascara.sum()) - n_nucleo,
        })
    clusters.sort(key=lambda c: c["tamano"], reverse=True)
    return clusters


def detectar_grupos(posiciones, eps=EPS_DEFECTO, min_samples=MIN_SAMPLES_DEFECTO,
                    algoritmo=ALGORITMO_DEFECTO):
    """Aplica DBSCAN a las posiciones [x, y] de un instante.

    Devuelve (etiquetas, clusters):
      etiquetas : np.ndarray (n,) con la etiqueta de cada agente, -1 = ruido.
      clusters  : lista de dicts {id, tamano, centro_x, centro_y, n_nucleo, n_frontera},
                  ordenada por tamano.
    """
    X = _como_matriz(posiciones)
    etiquetas, es_nucleo = _ajustar(X, eps, min_samples, algoritmo)
    return etiquetas, _resumir_clusters(X, etiquetas, es_nucleo)


def clasificar_puntos(posiciones, eps=EPS_DEFECTO, min_samples=MIN_SAMPLES_DEFECTO,
                      algoritmo=ALGORITMO_DEFECTO):
    """Como detectar_grupos, pero ademas clasifica cada agente.

    Devuelve (etiquetas, tipos, clusters):
      tipos : np.ndarray (n,) de int8 con TIPO_NUCLEO (2), TIPO_FRONTERA (1) o
              TIPO_RUIDO (0).
        NUCLEO   : tiene al menos min_samples puntos (contandose a si mismo) a
                   distancia <= eps.
        FRONTERA : no es nucleo, pero esta a distancia <= eps de un nucleo.
        RUIDO    : no es nucleo ni alcanzable desde uno (etiqueta -1).
    """
    X = _como_matriz(posiciones)
    etiquetas, es_nucleo = _ajustar(X, eps, min_samples, algoritmo)
    return etiquetas, _tipos(etiquetas, es_nucleo), _resumir_clusters(X, etiquetas, es_nucleo)


def calidad_agrupamiento(posiciones, etiquetas):
    """Silhouette y Davies-Bouldin, solo si hay al menos 2 clusters.

    El ruido (-1) se excluye del calculo porque no es un grupo.
    Devuelve (silhouette, davies_bouldin); (None, None) si no se pueden calcular.
    """
    X = _como_matriz(posiciones)
    etiquetas = np.asarray(etiquetas)
    mascara = etiquetas != -1
    n_grupos = len(set(etiquetas[mascara].tolist()))
    if n_grupos < 2 or n_grupos > int(mascara.sum()) - 1:
        return None, None
    Xc, lc = X[mascara], etiquetas[mascara]
    return float(silhouette_score(Xc, lc)), float(davies_bouldin_score(Xc, lc))


def proporcion_ruido(etiquetas):
    etiquetas = np.asarray(etiquetas)
    return float(np.mean(etiquetas == -1)) if len(etiquetas) else 0.0


def analizar_instante(posiciones, eps=EPS_DEFECTO, min_samples=MIN_SAMPLES_DEFECTO,
                      algoritmo=ALGORITMO_DEFECTO, con_metricas=True):
    """Analisis completo de un instante en una sola llamada.

    Devuelve un dict con: etiquetas, tipos, clusters, n_agentes, n_nucleo, n_frontera,
    n_ruido, pct_ruido, silhouette, davies_bouldin (None si hay < 2 grupos o
    con_metricas=False), tiempo_dbscan_ms y tiempo_metricas_ms.
    """
    X = _como_matriz(posiciones)
    t0 = time.perf_counter()
    etiquetas, es_nucleo = _ajustar(X, eps, min_samples, algoritmo)
    tipos = _tipos(etiquetas, es_nucleo)
    clusters = _resumir_clusters(X, etiquetas, es_nucleo)
    t1 = time.perf_counter()
    sil = dbi = None
    if con_metricas:
        sil, dbi = calidad_agrupamiento(X, etiquetas)
    t2 = time.perf_counter()
    return {
        "etiquetas": etiquetas, "tipos": tipos, "clusters": clusters,
        "n_agentes": int(len(X)),
        "n_nucleo": int(np.count_nonzero(tipos == TIPO_NUCLEO)),
        "n_frontera": int(np.count_nonzero(tipos == TIPO_FRONTERA)),
        "n_ruido": int(np.count_nonzero(tipos == TIPO_RUIDO)),
        "pct_ruido": 100.0 * proporcion_ruido(etiquetas),
        "silhouette": sil, "davies_bouldin": dbi,
        "tiempo_dbscan_ms": (t1 - t0) * 1000.0,
        "tiempo_metricas_ms": (t2 - t1) * 1000.0,
    }


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


if __name__ == "__main__":
    # Autoprueba rapida: dos grupos densos y dos puntos aislados.
    rng = np.random.default_rng(0)
    X = np.vstack([rng.normal([10, 10], 0.4, (30, 2)),
                   rng.normal([20, 5], 0.4, (30, 2)),
                   [[1, 1], [28, 18]]])
    r = analizar_instante(X)
    print(f"grupos={len(r['clusters'])} nucleo={r['n_nucleo']} frontera={r['n_frontera']} "
          f"ruido={r['n_ruido']} silhouette={r['silhouette']:.3f} "
          f"DBI={r['davies_bouldin']:.3f} dbscan={r['tiempo_dbscan_ms']:.2f} ms")
