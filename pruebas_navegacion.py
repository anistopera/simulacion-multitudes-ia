# -*- coding: utf-8 -*-
"""
Pruebas del módulo de navegación adaptativa (A*) y del esbozo de PSO.
Responsable: Orellana Castro Keyla

Ejecutar:  python pruebas_navegacion.py
"""
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA))

import math
import numpy as np

from modulos.entorno import Entorno
from modulos.navegacion_astar import (NavegadorAdaptativo, astar, costo_ruta,
                                      longitud_ruta, punto_a_celda, densidad_a_D)
from modulos.optimizacion_pso import pso
from demo_navegacion import (mapa_densidad_sintetico, agente_en_entrada,
                             rutas_A_y_B, escala_de_cambio)


def ruta_cruza_paso(entorno, celdas, fila_min, fila_max):
    """True si la ruta cruza la barrera (columna 15) dentro de las filas dadas."""
    return any(c == 15 and fila_min <= f < fila_max for f, c in celdas)


def main():
    ent = Entorno(configuracion=str(CARPETA / 'configuracion.json'))
    ini = punto_a_celda(ent, *ent.entrada)
    fin = punto_a_celda(ent, *ent.salida)
    D = mapa_densidad_sintetico()

    # 1. Sin congestión: camino más corto, recto por el paso principal (28 m)
    celdas, costo = astar(ent, ini, fin)
    assert abs(costo - 28.0) < 1e-9 and ruta_cruza_paso(ent, celdas, 10, 12)
    print('1. A* sin congestión: 28,0 m por el paso principal ... OK')

    # 2. Ninguna ruta atraviesa obstáculos ni corta esquinas
    for alpha in (0, 2, 5):
        r, _ = astar(ent, ini, fin, D, alpha)
        assert all(ent.mapa[f, c] == 0 for f, c in r)
    print('2. Rutas libres de obstáculos (alpha 0, 2, 5) ... OK')

    # 3. Con congestión, el costo adaptativo de B es menor que el de la ruta fija A
    A, B = rutas_A_y_B(ent, D)
    assert ruta_cruza_paso(ent, A, 10, 12) and ruta_cruza_paso(ent, B, 4, 7)
    assert costo_ruta(ent, B, D, 2.0) < costo_ruta(ent, A, D, 2.0)
    print('3. Con congestión A cruza por el principal y B por la alternativa ... OK')

    # 4. Optimalidad: A* coincide con Dijkstra (heurística nula) en costo
    import modulos.navegacion_astar as na
    _, c_astar = astar(ent, ini, fin, D, 2.0)
    # Dijkstra por relajación de Bellman-Ford sobre la cuadrícula (referencia independiente)
    Dc = na._D_por_celda(ent, D)
    dist = np.full(ent.mapa.shape, np.inf)
    dist[ini] = 0.0
    for _ in range(200):
        previo = dist.copy()
        for f in range(ent.filas):
            for c in range(ent.columnas):
                if ent.mapa[f, c] or math.isinf(previo[f, c]):
                    continue
                for df, dc in na.VECINOS:
                    nf, nc = f + df, c + dc
                    if not (0 <= nf < ent.filas and 0 <= nc < ent.columnas) or ent.mapa[nf, nc]:
                        continue
                    if df and dc and (ent.mapa[f + df, c] or ent.mapa[f, c + dc]):
                        continue
                    l = math.sqrt(2) if df and dc else 1.0
                    dist[nf, nc] = min(dist[nf, nc], previo[f, c] + l * (1 + 2.0 * Dc[nf, nc]))
        if np.array_equal(previo, dist):
            break
    assert abs(dist[fin] - c_astar) < 1e-9
    print(f'4. A* es óptimo (costo {c_astar:.3f} = referencia independiente) ... OK')

    # 5. Modo A no cambia nunca la ruta
    a = agente_en_entrada(ent)
    nav = NavegadorAdaptativo(ent, 'A')
    nav.asignar_ruta_inicial(a, 0.0, D)
    ruta0 = list(a['ruta'])
    for t in range(1, 30):
        assert not nav.actualizar(a, float(t), D)
    assert a['ruta'] == ruta0
    print('5. Modo A mantiene la ruta fija ... OK')

    # 6. Anti-oscilación: intervalo mínimo tau
    a = agente_en_entrada(ent)
    nav = NavegadorAdaptativo(ent, 'B', tau=4.0, margen=0.10)
    nav.asignar_ruta_inicial(a, 0.0, None)          # sale por el paso principal
    assert not nav.actualizar(a, 3.9, D) and nav.recalculos == 0   # antes de tau: no recalcula
    assert nav.actualizar(a, 4.0, D) and nav.recalculos == 1       # en tau: recalcula y se desvía
    print('6. Respeta el intervalo mínimo tau ... OK')

    # 7. Anti-oscilación: mejora mínima (margen)
    a = agente_en_entrada(ent)
    nav = NavegadorAdaptativo(ent, 'B', tau=0.0, margen=0.10)
    nav.asignar_ruta_inicial(a, 0.0, None)
    s_u = escala_de_cambio(ent, D)                   # escala donde B empieza a preferir el desvío
    D_leve = D * (s_u + 0.02)                        # apenas más congestión: la mejora es < 10 %
    assert not nav.actualizar(a, 1.0, D_leve) and nav.rechazos == 1
    print('7. Descarta rutas que no mejoran el costo en el margen ... OK')

    # 8. Sin alternativa viable: mantiene la ruta actual
    ent2 = Entorno(configuracion=str(CARPETA / 'configuracion.json'))
    for y in range(4, 7):
        ent2.agregar_obstaculo(15, y + 0.5)          # se cierra la ruta alternativa
    a = agente_en_entrada(ent2)
    nav = NavegadorAdaptativo(ent2, 'B', tau=0.0)
    nav.asignar_ruta_inicial(a, 0.0, None)
    ruta0 = list(a['ruta'])
    nav.actualizar(a, 1.0, D)                        # único camino: el principal
    assert a['ruta'] == ruta0 and nav.cambios == 0
    print('8. Sin alternativa viable mantiene la ruta actual ... OK')

    # 9. Se acepta objeto con atributos (no solo dict) y destino por defecto
    class Ag:
        pass
    o = Ag()
    o.id, o.x, o.y, o.ruta = 7, 1.0, 11.0, []
    NavegadorAdaptativo(ent, 'B').actualizar(o, 0.0, D)
    assert len(o.ruta) > 0
    print('9. Funciona con agentes tipo objeto ... OK')

    # 10. Densidad -> D
    assert np.allclose(densidad_a_D([0, 1, 2, 5]), [0, 0.5, 1, 1])
    print('10. D = min(1; densidad/2,0) ... OK')

    # 11. PSO: converge en una función de prueba con mínimo conocido
    objetivo = np.array([2.0, 1.0, 1.5])
    mejor, J, hist = pso(lambda th: float(np.sum((th - objetivo) ** 2)),
                         n_particulas=12, iteraciones=30, semilla=3)
    assert J < 0.05 and hist[-1] <= hist[0]
    print(f'11. Esbozo de PSO converge en función de prueba (J = {J:.4f}) ... OK')

    print('\nTODAS LAS PRUEBAS DE NAVEGACIÓN EXITOSAS')


if __name__ == '__main__':
    main()
