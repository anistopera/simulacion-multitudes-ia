# -*- coding: utf-8 -*-
"""
Módulo 7: Navegación adaptativa (A*)
Responsable: Orellana Castro Keyla

Qué hace este módulo
--------------------
Calcula rutas sobre la cuadrícula del Entorno con A*, usando el costo

    c(e, t) = L(e) * [1 + alpha * D(e, t)]

donde L(e) es la longitud del tramo (m), D(e, t) en [0, 1] es la congestión
que entrega el módulo de diagnóstico y alpha >= 0 es el peso de la congestión.
La heurística es la distancia euclidiana al destino (admisible y consistente
porque la penalización nunca es negativa).

Modos
-----
Modo A: ruta fija. Se calcula una sola vez el camino más corto (D = 0).
Modo B: ruta adaptativa. Se recalcula con D(e, t), con dos reglas
        anti-oscilación:
          1) intervalo mínimo tau entre recálculos de un mismo agente;
          2) la ruta nueva solo se acepta si su costo es menor que el de la
             ruta actual en al menos `margen` (por defecto 10 %).
        Si no hay ruta nueva viable, el agente conserva la actual.

Acuerdos de interfaz (reparto del grupo)
----------------------------------------
Estado de agente: id, x, y, vx, vy, v_deseada, destino, ruta.
  - Acepta un dict o un objeto con esos atributos.
  - `destino` es (x, y) en metros; si falta se usa entorno.destino.
  - `ruta` es una lista de waypoints (x, y) en metros (centros de celda).
    ESTE FORMATO LO DEFINÍ YO porque el reparto no lo fija: si Jhosselin usa
    otro, solo hay que cambiar celdas_a_waypoints().
Costo de ruta: D es la matriz del diagnóstico por celdas de 2 x 2 m
  (forma = (alto/2, ancho/2) = (10, 15)), con D = min(1, densidad / 2,0).
  La cuadrícula de A* es de 1 x 1 m, así que cada celda de A* usa el D de la
  celda de 2 x 2 m que la contiene.
"""
import heapq
import math

import numpy as np

SQRT2 = math.sqrt(2.0)
# (d_fila, d_columna): 4 vecinos ortogonales y 4 diagonales
VECINOS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

# Valores por defecto (el informe da solo rangos: alpha 0-5, tau 2-6 s).
# Son una decisión inicial, a calibrar (alpha lo calibrará el PSO; tau y
# margen se prueban a mano).
ALPHA_DEFECTO = 2.0
TAU_DEFECTO = 4.0
MARGEN_DEFECTO = 0.10
TAM_CELDA_D = 2.0  # lado de la celda del diagnóstico, en metros


# ----------------------------------------------------------------------
# Utilidades de conversión
# ----------------------------------------------------------------------
def densidad_a_D(densidad):
    """D(e,t) = min(1; densidad / 2,0), con densidad en agentes/m²."""
    return np.minimum(1.0, np.asarray(densidad, dtype=float) / 2.0)


def _D_por_celda(entorno, D, tam_celda_D=TAM_CELDA_D):
    """Expande la matriz D (celdas de 2x2 m) a la cuadrícula de A* (1x1 m)."""
    forma = (entorno.filas, entorno.columnas)
    if D is None:
        return np.zeros(forma)
    D = np.clip(np.asarray(D, dtype=float), 0.0, 1.0)
    filas = (np.arange(entorno.filas) * entorno.tam_celda / tam_celda_D).astype(int)
    cols = (np.arange(entorno.columnas) * entorno.tam_celda / tam_celda_D).astype(int)
    filas = np.clip(filas, 0, D.shape[0] - 1)
    cols = np.clip(cols, 0, D.shape[1] - 1)
    return D[np.ix_(filas, cols)]


def celda_a_punto(entorno, celda):
    """Centro de la celda (fila, columna) como (x, y) en metros."""
    fila, col = celda
    return ((col + 0.5) * entorno.tam_celda, (fila + 0.5) * entorno.tam_celda)


def punto_a_celda(entorno, x, y):
    """Celda libre que contiene a (x, y); si no existe, la libre más cercana."""
    celda = entorno.obtener_celda(x, y)
    if celda is not None and entorno.mapa[celda] == 0:
        return celda
    libres = np.argwhere(entorno.mapa == 0)
    centros = (libres + 0.5) * entorno.tam_celda  # columnas: y, x
    k = int(np.argmin((centros[:, 1] - x) ** 2 + (centros[:, 0] - y) ** 2))
    return (int(libres[k][0]), int(libres[k][1]))


def celdas_a_waypoints(entorno, celdas):
    return [celda_a_punto(entorno, c) for c in celdas]


# ----------------------------------------------------------------------
# A*
# ----------------------------------------------------------------------
def astar(entorno, inicio, destino, D=None, alpha=0.0, tam_celda_D=TAM_CELDA_D):
    """
    A* sobre la cuadrícula del Entorno (8 vecinos, sin cortar esquinas).

    inicio, destino: celdas (fila, columna).
    Devuelve (lista de celdas, costo) o (None, inf) si no hay camino.
    """
    if alpha < 0:
        raise ValueError('alpha debe ser >= 0 (si no, la heurística no es admisible)')
    inicio, destino = tuple(inicio), tuple(destino)
    mapa = entorno.mapa
    if mapa[inicio] or mapa[destino]:
        return None, math.inf
    Dc = _D_por_celda(entorno, D, tam_celda_D)
    tam = entorno.tam_celda
    filas, cols = mapa.shape

    def h(f, c):
        return tam * math.hypot(f - destino[0], c - destino[1])

    g = {inicio: 0.0}
    padre = {}
    cerrados = set()
    contador = 0
    abiertos = [(h(*inicio), contador, inicio)]
    while abiertos:
        _, _, actual = heapq.heappop(abiertos)
        if actual in cerrados:
            continue
        if actual == destino:
            ruta = [actual]
            while ruta[-1] in padre:
                ruta.append(padre[ruta[-1]])
            return ruta[::-1], g[actual]
        cerrados.add(actual)
        fa, ca = actual
        for df, dc in VECINOS:
            nf, nc = fa + df, ca + dc
            if not (0 <= nf < filas and 0 <= nc < cols) or mapa[nf, nc]:
                continue
            if df and dc and (mapa[fa + df, ca] or mapa[fa, ca + dc]):
                continue  # no cortar esquinas de paredes
            vecino = (nf, nc)
            if vecino in cerrados:
                continue
            largo = tam * (SQRT2 if (df and dc) else 1.0)
            nuevo = g[actual] + largo * (1.0 + alpha * Dc[nf, nc])
            if nuevo < g.get(vecino, math.inf):
                g[vecino] = nuevo
                padre[vecino] = actual
                contador += 1
                heapq.heappush(abiertos, (nuevo + h(nf, nc), contador, vecino))
    return None, math.inf


def costo_ruta(entorno, celdas, D=None, alpha=0.0, tam_celda_D=TAM_CELDA_D):
    """Costo c(e,t) acumulado de una ruta (lista de celdas); inf si cruza un obstáculo."""
    Dc = _D_por_celda(entorno, D, tam_celda_D)
    total = 0.0
    for (f0, c0), (f1, c1) in zip(celdas, celdas[1:]):
        if entorno.mapa[f1, c1]:
            return math.inf
        largo = entorno.tam_celda * math.hypot(f1 - f0, c1 - c0)
        total += largo * (1.0 + alpha * Dc[f1, c1])
    return total


def longitud_ruta(entorno, celdas):
    """Longitud geométrica (m) de una ruta, sin penalización."""
    return costo_ruta(entorno, celdas, None, 0.0)


# ----------------------------------------------------------------------
# Acceso al estado del agente (dict u objeto)
# ----------------------------------------------------------------------
def _leer(agente, campo, defecto=None):
    if isinstance(agente, dict):
        return agente.get(campo, defecto)
    return getattr(agente, campo, defecto)


def _escribir(agente, campo, valor):
    if isinstance(agente, dict):
        agente[campo] = valor
    else:
        setattr(agente, campo, valor)


# ----------------------------------------------------------------------
# Navegador (modo A / modo B)
# ----------------------------------------------------------------------
class NavegadorAdaptativo:
    """
    Uso típico (lo llama el programa principal, una vez por segundo de
    simulación, después del diagnóstico):

        nav = NavegadorAdaptativo(entorno, modo='B')
        nav.actualizar_todos(agentes, t, D)

    `D` es la matriz del diagnóstico (celdas de 2x2 m, valores en [0, 1]).
    En modo A se ignora D y la ruta nunca cambia.
    """

    def __init__(self, entorno, modo='B', alpha=ALPHA_DEFECTO, tau=TAU_DEFECTO,
                 margen=MARGEN_DEFECTO, tam_celda_D=TAM_CELDA_D):
        modo = str(modo).upper()
        if modo not in ('A', 'B'):
            raise ValueError("modo debe ser 'A' o 'B'")
        if alpha < 0 or tau < 0 or not 0 <= margen < 1:
            raise ValueError('alpha >= 0, tau >= 0 y 0 <= margen < 1')
        self.entorno = entorno
        self.modo = modo
        self.alpha = alpha
        self.tau = tau
        self.margen = margen
        self.tam_celda_D = tam_celda_D
        self.reiniciar()

    def reiniciar(self):
        self._ultimo_calculo = {}
        self.recalculos = 0        # veces que se ejecutó A* con costo adaptativo
        self.cambios = 0           # rutas nuevas aceptadas
        self.rechazos = 0          # rutas nuevas descartadas por margen insuficiente
        self.sin_alternativa = 0   # A* no encontró camino: se mantiene la actual
        self.cambios_por_agente = {}

    # -- planificación inicial (ambos modos) ----------------------------
    def asignar_ruta_inicial(self, agente, t=0.0, D=None):
        if self.modo == 'A':
            D, alpha = None, 0.0
        else:
            alpha = self.alpha
        inicio = punto_a_celda(self.entorno, _leer(agente, 'x'), _leer(agente, 'y'))
        destino = self._celda_destino(agente)
        celdas, _ = astar(self.entorno, inicio, destino, D, alpha, self.tam_celda_D)
        if celdas is None:
            self.sin_alternativa += 1
            return False
        _escribir(agente, 'ruta', celdas_a_waypoints(self.entorno, celdas))
        self._ultimo_calculo[_leer(agente, 'id')] = t
        return True

    # -- recálculo (solo modo B) ----------------------------------------
    def actualizar(self, agente, t, D=None):
        """Devuelve True si la ruta del agente cambió en esta llamada."""
        if not _leer(agente, 'ruta'):
            return self.asignar_ruta_inicial(agente, t, D)
        if self.modo == 'A':
            return False
        aid = _leer(agente, 'id')
        if t - self._ultimo_calculo.get(aid, -math.inf) < self.tau:
            return False                       # regla 1: intervalo mínimo
        self._ultimo_calculo[aid] = t
        inicio = punto_a_celda(self.entorno, _leer(agente, 'x'), _leer(agente, 'y'))
        actual = self._cola_ruta_actual(agente, inicio)
        if len(actual) <= 1:
            return False                       # ya llegó
        self.recalculos += 1
        nueva, c_nueva = astar(self.entorno, inicio, actual[-1], D, self.alpha,
                               self.tam_celda_D)
        if nueva is None:
            self.sin_alternativa += 1          # sin alternativa: mantener la actual
            return False
        if nueva == actual:
            return False
        c_actual = costo_ruta(self.entorno, actual, D, self.alpha, self.tam_celda_D)
        if c_nueva < c_actual * (1.0 - self.margen):   # regla 2: mejora mínima
            _escribir(agente, 'ruta', celdas_a_waypoints(self.entorno, nueva))
            self.cambios += 1
            self.cambios_por_agente[aid] = self.cambios_por_agente.get(aid, 0) + 1
            return True
        self.rechazos += 1
        return False

    def actualizar_todos(self, agentes, t, D=None):
        """Aplica actualizar() a todos los agentes; devuelve cuántas rutas cambiaron."""
        return sum(1 for a in agentes if self.actualizar(a, t, D))

    # -- auxiliares ------------------------------------------------------
    def _celda_destino(self, agente):
        destino = _leer(agente, 'destino', None)
        if destino is None:
            destino = self.entorno.destino
        return punto_a_celda(self.entorno, destino[0], destino[1])

    def _cola_ruta_actual(self, agente, celda_agente):
        """Tramo de la ruta vigente que le falta recorrer al agente, como celdas."""
        ruta = _leer(agente, 'ruta')
        celdas = [punto_a_celda(self.entorno, p[0], p[1]) for p in ruta]
        x, y = _leer(agente, 'x'), _leer(agente, 'y')
        k = int(np.argmin([(p[0] - x) ** 2 + (p[1] - y) ** 2 for p in ruta]))
        cola = celdas[k:]
        if cola[0] != celda_agente:
            cola = [celda_agente] + cola
        return cola
