"""Calibración reproducible PSO con episodios reales del simulador.

Colocar en scripts_analisis/calibrar_pso.py y ejecutar desde la raíz:
    python -m scripts_analisis.calibrar_pso --particulas 4 --iteraciones 3

Las semillas de calibración (por defecto 101 y 102) no se utilizan
para la comparación final (42, 43 y 44). No altera main.py.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from main import CAPTURAS, ejecutar_episodio, validar_theta
from modulos.optimizacion_pso import LIMITES, pso, costo_J


def guardar_csv(ruta, filas):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(filas[0]))
        writer.writeheader()
        writer.writerows(filas)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--particulas', type=int, default=4)
    parser.add_argument('--iteraciones', type=int, default=3)
    parser.add_argument('--semillas', type=int, nargs='+', default=[101, 102])
    parser.add_argument('--agentes', type=int, choices=(40, 80, 120), default=40)
    parser.add_argument('--semilla-pso', type=int, default=2026)
    parser.add_argument('--salida', type=Path, default=CAPTURAS)
    args = parser.parse_args(argv)
    if args.particulas < 2 or args.iteraciones < 1:
        parser.error('Se requieren al menos 2 partículas y 1 iteración')
    if len(set(args.semillas)) != len(args.semillas) or set(args.semillas) & {42, 43, 44}:
        parser.error('Las semillas deben ser únicas y distintas de 42, 43 y 44')

    salida = args.salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)
    carpeta_corridas = salida / 'calibracion_pso'  # no mezcla con los CSV finales
    carpeta_corridas.mkdir(exist_ok=True)
    print('Calculando bases del modo A...', flush=True)
    bases = {}
    for semilla in args.semillas:
        bases[semilla] = ejecutar_episodio(
            args.agentes, 'A', semilla, carpeta_salida=carpeta_corridas)

    historial_evaluaciones = []
    cache = {}

    def evaluar(theta):
        theta = validar_theta([float(x) for x in theta])
        clave = tuple(round(x, 12) for x in theta)
        if clave in cache:
            return cache[clave]
        costos = []
        for semilla in args.semillas:
            resultado = ejecutar_episodio(
                args.agentes, 'B_PSO', semilla,
                carpeta_salida=carpeta_corridas, theta=theta)
            base = bases[semilla]
            # Normalización explícita para evitar denominadores nulos.
            # T0 > 0 normalmente; E0 y S0 pueden ser cero.
            base_segura = dict(base)
            base_segura['tiempo_transito'] = max(float(base['tiempo_transito']), 1e-9)
            base_segura['tiempo_espera'] = max(float(base['tiempo_espera']), 1.0)
            base_segura['solapamientos'] = max(float(base['solapamientos']), 1.0)
            valor = float(costo_J(resultado, base_segura))
            if not math.isfinite(valor):
                raise ValueError('La función de costo devolvió un valor no finito')
            costos.append(valor)
        promedio = float(np.mean(costos))
        cache[clave] = promedio
        historial_evaluaciones.append({
            'evaluacion': len(historial_evaluaciones) + 1,
            'alpha': theta[0], 'ks': theta[1], 'kr': theta[2],
            'costo_medio': promedio, 'costos_por_semilla': json.dumps(costos),
        })
        guardar_csv(salida / 'evaluaciones_pso.csv', historial_evaluaciones)
        print(f"Evaluación {len(historial_evaluaciones)}: theta={tuple(round(x, 4) for x in theta)}, J={promedio:.6f}", flush=True)
        return promedio

    theta, mejor_j, convergencia = pso(
        evaluar, limites=LIMITES, n_particulas=args.particulas,
        iteraciones=args.iteraciones, semilla=args.semilla_pso)
    alpha, ks, kr = validar_theta(theta.tolist())
    payload = {
        'theta': {'alpha': alpha, 'ks': ks, 'kr': kr},
        'mejor_J': float(mejor_j),
        'semillas_calibracion': args.semillas,
        'agentes_calibracion': args.agentes,
        'semilla_pso': args.semilla_pso,
        'particulas': args.particulas,
        'iteraciones': args.iteraciones,
        'normalizacion_cero': 'E0 y S0 usan piso de 1 unidad cuando son cero',
    }
    (salida / 'theta_optimo.json').write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    guardar_csv(salida / 'historial_convergencia_pso.csv', [
        {'iteracion': i, 'mejor_J': float(j)} for i, j in enumerate(convergencia)])

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(range(len(convergencia)), convergencia, marker='o')
    ax.set(xlabel='Iteración PSO (0 = inicialización)', ylabel='Mejor costo J',
           title='Convergencia de la calibración PSO')
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(salida / 'convergencia_pso.png', dpi=180)
    plt.close(fig)
    print('\nCalibración terminada. Mejor J:', mejor_j)
    print('Theta:', payload['theta'])
    print('Resultados en:', salida)


if __name__ == '__main__':
    main()
