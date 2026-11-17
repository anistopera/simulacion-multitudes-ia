# -*- coding: utf-8 -*-
"""
ESBOZO de PSO para calibrar theta = [alpha, ks, kr]   (NO integrado todavía)
Responsable: Orellana Castro Keyla

Es un esbozo: el optimizador funciona, pero la función `evaluar(theta)` debe
conectarse a la simulación completa (la arma Padilla). Cada evaluación = una
simulación entera, así que el PSO se corre por lotes, fuera de la ejecución
interactiva. Las semillas de calibración deben ser distintas de las de la
comparación final (sección 3.10 del informe).

Función de costo (sección 3.9 del informe):
    J = 0,50*T/T0 + 0,30*E/E0 + 0,20*S/S0 + LAMBDA*(1 - tasa_finalizacion)
con T = tiempo de tránsito, E = tiempo de espera, S = solapamientos y
T0, E0, S0 los valores de la simulación sin adaptación (modo A).
LAMBDA = 1,0 es una decisión mía (el informe pide una penalización por agentes
que no llegan, pero no da su peso).
"""
import numpy as np

LIMITES = {'alpha': (0.0, 5.0), 'ks': (0.5, 2.0), 'kr': (0.5, 3.0)}
PESOS = (0.50, 0.30, 0.20)
LAMBDA = 1.0


def costo_J(metricas, base):
    """metricas/base: dict con tiempo_transito, tiempo_espera, solapamientos, tasa_finalizacion."""
    t = metricas['tiempo_transito'] / base['tiempo_transito']
    e = metricas['tiempo_espera'] / max(base['tiempo_espera'], 1e-9)
    s = metricas['solapamientos'] / max(base['solapamientos'], 1)  # evita dividir entre 0
    no_llegan = 1.0 - metricas['tasa_finalizacion']
    return PESOS[0] * t + PESOS[1] * e + PESOS[2] * s + LAMBDA * no_llegan


def pso(evaluar, limites=LIMITES, n_particulas=10, iteraciones=15,
        w=0.7, c1=1.5, c2=1.5, semilla=0):
    """
    PSO clásico (Kennedy y Eberhart, 1995).
    evaluar(theta: np.ndarray) -> J (menor es mejor).
    Devuelve (mejor_theta, mejor_J, historial_de_mejor_J).
    """
    rng = np.random.default_rng(semilla)
    bajo = np.array([v[0] for v in limites.values()])
    alto = np.array([v[1] for v in limites.values()])
    pos = rng.uniform(bajo, alto, size=(n_particulas, len(bajo)))
    vel = rng.uniform(-(alto - bajo), alto - bajo, size=pos.shape) * 0.1
    mejor_p = pos.copy()
    mejor_pJ = np.array([evaluar(p) for p in pos])
    g = int(np.argmin(mejor_pJ))
    mejor_g, mejor_gJ = mejor_p[g].copy(), float(mejor_pJ[g])
    historial = [mejor_gJ]
    for _ in range(iteraciones):
        r1, r2 = rng.random(pos.shape), rng.random(pos.shape)
        vel = w * vel + c1 * r1 * (mejor_p - pos) + c2 * r2 * (mejor_g - pos)
        pos = np.clip(pos + vel, bajo, alto)
        for i in range(n_particulas):
            J = evaluar(pos[i])
            if J < mejor_pJ[i]:
                mejor_pJ[i], mejor_p[i] = J, pos[i].copy()
                if J < mejor_gJ:
                    mejor_gJ, mejor_g = float(J), pos[i].copy()
        historial.append(mejor_gJ)
    return mejor_g, mejor_gJ, historial
