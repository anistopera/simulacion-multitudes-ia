# -*- coding: utf-8 -*-
"""
Demo de navegación adaptativa: genera la comparación visual de rutas A vs B.
Responsable: Orellana Castro Keyla

Ejecutar desde la raíz del proyecto:
    python -m demos.demo_navegacion

Genera capturas/comparacion_rutas_A_vs_B.png y imprime los números del informe.
Usa un mapa de densidad SINTÉTICO (una cola frente al paso principal) para
inspeccionar el planificador de forma aislada del ciclo integrado de main.py.
"""
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CARPETA))

import numpy as np
import matplotlib
if '--no-mostrar' in sys.argv:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from modulos.entorno import Entorno
from modulos.navegacion_astar import (NavegadorAdaptativo, astar, costo_ruta,
                                      longitud_ruta, punto_a_celda,
                                      ALPHA_DEFECTO, TAU_DEFECTO, MARGEN_DEFECTO)

AZUL, NARANJA = '#2a78d6', '#eb6834'      # B (adaptativa), A (fija)
TINTA, TINTA2, PARED = '#0b0b0b', '#52514e', '#37474F'


def mapa_densidad_sintetico(escala=1.0):
    """D(e,t) de 10x15 celdas de 2x2 m: cola frente al paso principal (x 10-16, y 8-14)."""
    D = np.zeros((10, 15))
    D[5, 7] = D[5, 6] = 1.0
    D[5, 5] = 0.8
    D[4, 6] = D[4, 7] = D[6, 6] = D[6, 7] = 0.7
    D[4, 5] = D[6, 5] = 0.4
    D[5, 8] = 0.4
    return D * escala


def agente_en_entrada(entorno, i=0):
    return {'id': i, 'x': float(entorno.entrada[0]), 'y': float(entorno.entrada[1]),
            'vx': 0.0, 'vy': 0.0, 'v_deseada': 1.2, 'destino': entorno.destino, 'ruta': []}


def rutas_A_y_B(entorno, D, alpha=ALPHA_DEFECTO):
    a, b = agente_en_entrada(entorno), agente_en_entrada(entorno, 1)
    nav_a = NavegadorAdaptativo(entorno, 'A', alpha=alpha)
    nav_b = NavegadorAdaptativo(entorno, 'B', alpha=alpha)
    nav_a.asignar_ruta_inicial(a, 0.0, D)
    nav_b.asignar_ruta_inicial(b, 0.0, D)
    celdas = lambda ag: [punto_a_celda(entorno, p[0], p[1]) for p in ag['ruta']]
    return celdas(a), celdas(b)


def escala_de_cambio(entorno, D_base, alpha=ALPHA_DEFECTO):
    """Menor escala de congestión (0-1) con la que B deja de usar el paso principal."""
    ruta_a, _ = rutas_A_y_B(entorno, None, alpha)
    for s in np.linspace(0, 1, 201):
        _, rb = rutas_A_y_B(entorno, D_base * s, alpha)
        if rb != ruta_a:
            return float(s)
    return None


def simular_oscilacion(entorno, D_base, s_umbral, tau, margen, alpha=ALPHA_DEFECTO,
                       duracion=60, semilla=1):
    """Agente quieto en la entrada; la congestión oscila alrededor del umbral de cambio."""
    rng = np.random.default_rng(semilla)
    nav = NavegadorAdaptativo(entorno, 'B', alpha=alpha, tau=tau, margen=margen)
    ag = agente_en_entrada(entorno)
    nav.asignar_ruta_inicial(ag, 0.0, D_base * (s_umbral + 0.10))
    acumulado = []
    for t in range(1, duracion + 1):
        s = np.clip(s_umbral + 0.08 * np.sin(2 * np.pi * t / 6) + 0.04 * rng.normal(), 0, 1)
        nav.actualizar(ag, float(t), D_base * s)
        acumulado.append(nav.cambios)
    return acumulado


def dibujar_mapa(ax, entorno, D=None):
    ax.imshow(entorno.mapa, origin='lower', extent=(0, entorno.ancho, 0, entorno.alto),
              cmap=ListedColormap(['#fcfcfb', PARED]), vmin=0, vmax=1, interpolation='nearest')
    if D is not None:
        im = ax.imshow(D, origin='lower', extent=(0, entorno.ancho, 0, entorno.alto),
                       cmap='YlOrRd', vmin=0, vmax=1, alpha=np.where(D > 0, 0.55, 0.0),
                       interpolation='nearest')
    ax.plot(*entorno.entrada, marker='>', color=TINTA, ms=9, ls='')
    ax.plot(*entorno.salida, marker='*', color=TINTA, ms=12, ls='')
    ax.text(entorno.entrada[0] + 0.4, entorno.entrada[1] + 1.0, 'Entrada', fontsize=8, color=TINTA2)
    ax.text(entorno.salida[0] - 3.0, entorno.salida[1] + 1.0, 'Salida', fontsize=8, color=TINTA2)
    ax.set_xlim(0, entorno.ancho)
    ax.set_ylim(0, entorno.alto)
    ax.set_aspect('equal')
    ax.set_xlabel('x (m)', color=TINTA2)
    ax.set_ylabel('y (m)', color=TINTA2)
    ax.tick_params(colors=TINTA2, labelsize=8)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)


def trazar(ax, entorno, celdas, color, estilo, etiqueta, desfase=0.0):
    pts = np.array([((c + 0.5) * entorno.tam_celda, (f + 0.5) * entorno.tam_celda + desfase)
                    for f, c in celdas])
    ax.plot(pts[:, 0], pts[:, 1], color=color, ls=estilo, lw=2.2, label=etiqueta,
            solid_capstyle='round')


def main():
    entorno = Entorno(configuracion=str(CARPETA / 'configuracion.json'))
    D_cong = mapa_densidad_sintetico()
    alpha = ALPHA_DEFECTO

    # --- Panel (a) y (b): rutas A y B ---
    A0, B0 = rutas_A_y_B(entorno, None, alpha)
    A1, B1 = rutas_A_y_B(entorno, D_cong, alpha)
    lA0, lB0 = longitud_ruta(entorno, A0), longitud_ruta(entorno, B0)
    lA1, lB1 = longitud_ruta(entorno, A1), longitud_ruta(entorno, B1)
    cA1 = costo_ruta(entorno, A1, D_cong, alpha)
    cB1 = costo_ruta(entorno, B1, D_cong, alpha)
    print(f'Sin congestión: A = {lA0:.1f} m, B = {lB0:.1f} m, iguales: {A0 == B0}')
    print(f'Con congestión (alpha={alpha}): A = {lA1:.1f} m, costo {cA1:.1f} | '
          f'B = {lB1:.1f} m, costo {cB1:.1f} | mejora de costo {100*(1-cB1/cA1):.0f} %')

    # --- Panel (c): anti-oscilación ---
    s_u = escala_de_cambio(entorno, D_cong, alpha)
    print(f'Escala de congestión a la que B cambia de paso: {s_u:.2f}')
    sin = simular_oscilacion(entorno, D_cong, s_u, tau=0.0, margen=0.0)
    con = simular_oscilacion(entorno, D_cong, s_u, tau=TAU_DEFECTO, margen=MARGEN_DEFECTO)
    print(f'Cambios de ruta en 60 s: sin reglas = {sin[-1]}, con tau={TAU_DEFECTO:g} s y '
          f'margen {MARGEN_DEFECTO:.0%} = {con[-1]}')

    plt.rcParams['font.family'] = 'DejaVu Sans'
    fig, ejes = plt.subplots(1, 3, figsize=(16, 5.2), gridspec_kw={'width_ratios': [1, 1, 0.9]})
    ax = ejes[0]
    dibujar_mapa(ax, entorno)
    trazar(ax, entorno, A0, NARANJA, '--', f'Modo A ({lA0:.1f} m)', desfase=0.25)
    trazar(ax, entorno, B0, AZUL, '-', f'Modo B ({lB0:.1f} m)', desfase=-0.25)
    ax.set_title('(a) Sin congestión: A y B coinciden', fontsize=10, color=TINTA, loc='left')
    ax.legend(loc='upper right', fontsize=8, frameon=False)

    ax = ejes[1]
    dibujar_mapa(ax, entorno, D_cong)
    trazar(ax, entorno, A1, NARANJA, '--', f'Modo A: ruta fija ({lA1:.1f} m, costo {cA1:.0f})')
    trazar(ax, entorno, B1, AZUL, '-', f'Modo B: se desvía ({lB1:.1f} m, costo {cB1:.0f})')
    ax.set_title('(b) Con congestión (D sintético, rojo): B usa la ruta alternativa',
                 fontsize=10, color=TINTA, loc='left')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.17), fontsize=8, frameon=False)

    ax = ejes[2]
    t = np.arange(1, 61)
    ax.step(t, sin, where='post', color=NARANJA, ls='--', lw=2, label=f'Sin reglas ({sin[-1]} cambios)')
    ax.step(t, con, where='post', color=AZUL, lw=2,
            label=f'τ = {TAU_DEFECTO:g} s y margen {MARGEN_DEFECTO:.0%} ({con[-1]} cambios)')
    ax.set_title('(c) Cambios de ruta acumulados', fontsize=10, color=TINTA, loc='left')
    ax.set_xlabel('Tiempo (s)', color=TINTA2)
    ax.set_ylabel('Cambios de ruta del agente', color=TINTA2)
    ax.tick_params(colors=TINTA2, labelsize=8)
    ax.grid(axis='y', alpha=0.2)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    ax.legend(loc='upper left', fontsize=8, frameon=False)

    fig.tight_layout()
    destino = CARPETA / 'capturas' / 'comparacion_rutas_A_vs_B.png'
    destino.parent.mkdir(exist_ok=True)
    fig.savefig(destino, dpi=200, bbox_inches='tight', facecolor='white')
    print('Imagen guardada en:', destino)
    if '--no-mostrar' not in sys.argv:
        plt.show()


if __name__ == '__main__':
    main()
