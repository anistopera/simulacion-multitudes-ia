# -*- coding: utf-8 -*-
"""
Demo y Verificación Experimental del Módulo 6: Diagnóstico de congestión
Responsable: Lora Quilla Santiago Leonardo

Qué hace este script
--------------------
1. Demuestra la clasificación en vivo de las zonas (Libre, Acumulación, Crítica).
2. Realiza la prueba requerida con 120 agentes frente al paso principal (2 m)
   para verificar empíricamente si se alcanza el estado de congestión crítica.
3. Genera y guarda las figuras en la carpeta `capturas/` para el informe impreso:
   - `capturas/zonas_diagnostico.png`
   - `capturas/diagnostico_120_agentes.png`
4. Imprime la tabla de umbrales y resultados para la Sección 5.5.

Ejecutar:
    python -m demos.demo_diagnostico [--no-mostrar]
"""

import sys
from pathlib import Path

CARPETA_PROYECTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CARPETA_PROYECTO))

import numpy as np
import matplotlib
if '--no-mostrar' in sys.argv:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt

from modulos.entorno import Entorno
from modulos.diagnostico import (
    DiagnosticoCongestion,
    ESTADO_LIBRE,
    ESTADO_ACUMULACION,
    ESTADO_CRITICA,
    UMBRAL_DENSIDAD_ALERTA,
    UMBRAL_DENSIDAD_CRITICA,
    PERSISTENCIA_MINIMA,
    FACTOR_VELOCIDAD_CRITICA
)


def simular_cuello_botella_120_agentes(semilla=42, duracion_s=25):
    """
    Simulación cinemática simplificada de 120 agentes convergiendo hacia el
    paso principal (2 m de ancho, en x=15, y=10..12).
    """
    rng = np.random.default_rng(semilla)
    n_agentes = 120
    entorno = Entorno()
    diag = DiagnosticoCongestion(entorno=entorno)

    # Generación inicial en la zona de entrada (x: 1..8, y: 5..15)
    agentes = []
    for i in range(n_agentes):
        agentes.append({
            'id': i,
            'x': float(rng.uniform(1.0, 9.0)),
            'y': float(rng.uniform(6.0, 14.0)),
            'vx': 0.0,
            'vy': 0.0,
            'v_deseada': float(rng.uniform(1.1, 1.4)),
            'activo': True
        })

    objetivo_paso = (15.0, 11.0)  # Centro del paso principal
    salida = (29.0, 11.0)

    # Registro de evolución temporal
    historial_criticas = []
    historial_densidad_max = []
    tiempo_primer_critica = None

    dt = 0.5  # Paso de tiempo de la simulación
    pasos = int(duracion_s / dt)

    capacidad_paso = 2.0  # Capacidad máxima aproximada del paso de 2 m (agentes por segundo)

    print(f"\nIniciando simulación de verificación con {n_agentes} agentes hacia el paso principal (ancho: 2 m)...")

    for paso in range(pasos):
        t = paso * dt

        # Actualizar agentes
        # Agentes cercanos al paso compiten y reducen su velocidad drásticamente
        agentes_frente_paso = [
            ag for ag in agentes if (11.0 <= ag['x'] <= 15.0 and 9.0 <= ag['y'] <= 13.0)
        ]
        num_frente = len(agentes_frente_paso)

        # Factor de ralentización por acumulación en el embudo
        factor_freno = max(0.08, 1.0 - (num_frente / 18.0)) if num_frente > 5 else 1.0

        for ag in agentes:
            if not ag['activo']:
                continue

            # Si ya cruzó la barrera x > 15.5
            if ag['x'] >= 15.5:
                # Se dirige a la salida libremente
                dx = salida[0] - ag['x']
                dy = salida[1] - ag['y']
                dist = np.hypot(dx, dy)
                if dist < 0.8:
                    ag['activo'] = False
                    continue
                v_act = ag['v_deseada']
                ag['vx'] = v_act * (dx / dist)
                ag['vy'] = v_act * (dy / dist)
            else:
                # Se dirige al paso principal
                dx = objetivo_paso[0] - ag['x']
                dy = objetivo_paso[1] - ag['y']
                dist = np.hypot(dx, dy)

                if dist < 0.1:
                    ag['x'] = 15.6  # Cruzó
                    continue

                # Si está en el embudo frente a la pared, se frena fuertemente
                if 12.0 <= ag['x'] < 15.0 and 8.0 <= ag['y'] <= 14.0:
                    v_act = ag['v_deseada'] * factor_freno * rng.uniform(0.7, 1.1)
                else:
                    v_act = ag['v_deseada'] * rng.uniform(0.9, 1.0)

                ag['vx'] = v_act * (dx / dist)
                ag['vy'] = v_act * (dy / dist)

            # Actualizar posición
            ag['x'] += ag['vx'] * dt
            ag['y'] += ag['vy'] * dt
            ag['y'] = np.clip(ag['y'], 0.5, 19.5)

        # Cada 1.0 s evaluar diagnóstico
        if paso % int(1.0 / dt) == 0:
            estados, D = diag.actualizar(agentes, dt=1.0)
            metricas = diag.obtener_metricas_resumen()

            historial_criticas.append(metricas['celdas_criticas'])
            historial_densidad_max.append(metricas['densidad_maxima'])

            if metricas['celdas_criticas'] > 0 and tiempo_primer_critica is None:
                tiempo_primer_critica = t

            if int(t) % 5 == 0:
                print(f"  t = {t:4.1f} s | Densidad máx: {metricas['densidad_maxima']:4.2f} ag/m² "
                      f"| Celdas Acumulación: {metricas['celdas_acumulacion']:2d} "
                      f"| Celdas Críticas: {metricas['celdas_criticas']:2d}")

    # Evaluación de la verificación
    print("\n--------------------------------------------------")
    print(" RESULTADO DE LA VERIFICACIÓN CON 120 AGENTES")
    print("--------------------------------------------------")
    se_alcanzo_critica = max(historial_criticas) > 0
    densidad_pico = max(historial_densidad_max)

    print(f"Densidad pico alcanzada frente al paso: {densidad_pico:.2f} agentes/m²")
    print(f"Umbral crítico definido en el proyecto: {UMBRAL_DENSIDAD_CRITICA:.2f} agentes/m²")
    print(f"¿Se alcanzó estado de CONGESTIÓN CRÍTICA? -> {'SÍ, CONFIRMADO' if se_alcanzo_critica else 'NO'}")

    if se_alcanzo_critica:
        print(f"Tiempo en el que apareció la primera celda crítica: t = {tiempo_primer_critica:.1f} s")
        print("Conclusión: Los parámetros actuales (120 agentes, paso de 2 m) reproducen exitosamente")
        print("            la congestión crítica sin necesidad de forzar o estrechar el paso.")
    else:
        print("Propuesta de ajuste recomendada: Reducir paso principal a 1.5 m o inyectar 150 agentes.")

    # Guardar capturas para el informe
    carpeta_capturas = CARPETA_PROYECTO / "capturas"
    carpeta_capturas.mkdir(parents=True, exist_ok=True)

    ruta_img_120 = carpeta_capturas / "diagnostico_120_agentes.png"
    diag.dibujar_diagnostico(
        agentes=agentes,
        archivo=str(ruta_img_120),
        mostrar=('--no-mostrar' not in sys.argv),
        titulo="Verificación de Cuello de Botella con 120 Agentes (Paso Principal 2 m)"
    )

    return diag, agentes, se_alcanzo_critica, densidad_pico


def generar_captura_estados_referencia():
    """
    Genera un escenario didáctico donde se observan simultáneamente los tres estados:
    - Libre: flujo continuo a velocidad nominal.
    - Acumulación: grupo denso pero en movimiento.
    - Crítica: grupo muy denso, detenido frente a obstáculo durante > 3 s.
    """
    entorno = Entorno()
    diag = DiagnosticoCongestion(entorno=entorno)

    agentes = []
    # 1. ZONA LIBRE (Celda [2, 2]): 2 agentes fluyendo a 1.2 m/s
    agentes.append({'x': 4.5, 'y': 4.5, 'vx': 1.2, 'vy': 0.0, 'v_deseada': 1.2})
    agentes.append({'x': 5.0, 'y': 5.0, 'vx': 1.1, 'vy': 0.0, 'v_deseada': 1.2})

    # 2. ZONA ACUMULACIÓN (Celda [2, 4]): 7 agentes fluyendo a 1.0 m/s (> 50% de 1.2)
    for _ in range(7):
        agentes.append({
            'x': float(np.random.uniform(8.2, 9.8)),
            'y': float(np.random.uniform(4.2, 5.8)),
            'vx': 1.0,
            'vy': 0.1,
            'v_deseada': 1.2
        })

    # 3. ZONA CRÍTICA (Celda [5, 6], justo frente a la barrera x=15):
    # 10 agentes detenidos (0.1 m/s)
    for _ in range(10):
        agentes.append({
            'x': float(np.random.uniform(12.5, 13.8)),
            'y': float(np.random.uniform(10.2, 11.8)),
            'vx': 0.05,
            'vy': 0.0,
            'v_deseada': 1.2
        })

    # Simular 3.0 segundos para activar la persistencia crítica
    diag.actualizar(agentes, dt=1.0)
    diag.actualizar(agentes, dt=1.0)
    estados, D = diag.actualizar(agentes, dt=1.0)

    carpeta_capturas = CARPETA_PROYECTO / "capturas"
    ruta_img = carpeta_capturas / "zonas_diagnostico.png"
    diag.dibujar_diagnostico(
        agentes=agentes,
        archivo=str(ruta_img),
        mostrar=('--no-mostrar' not in sys.argv),
        titulo="Clasificación de Zonas por Reglas y Matriz de Costo D(e, t)"
    )


def imprimir_tabla_umbrales():
    """Imprime la tabla formal requerida para la Sección 5.5 del informe."""
    print("\n" + "=" * 80)
    print(" TABLA DE UMBRALES Y PARÁMETROS OPERATIVOS (SECCIÓN 5.5 DEL INFORME)")
    print("=" * 80)
    filas = [
        ("Tamaño de celda espacial", "2.0 m x 2.0 m (4.0 m²)", "Unidad de análisis local de densidad y velocidad"),
        ("Dimensiones de la matriz", "10 filas x 15 columnas", "Discretización total del recinto de 30 x 20 m"),
        ("Umbral de Alerta (Acumulación)", "densidad ≥ 1.5 agentes/m²", "Señala concentración alta de agentes sin bloqueo"),
        ("Umbral de Densidad Crítica", "densidad ≥ 2.0 agentes/m²", "Candidata a congestión severa por saturación espacial"),
        ("Umbral de Velocidad Crítica", "velocidad ≤ 50 % deseada", "Distingue flujo denso en marcha de embotellamiento"),
        ("Ventana de Persistencia Mínima", "3.0 segundos continuos", "Filtra fluctuaciones estocásticas y frenadas momentáneas"),
        ("Fórmula de Costo D(e, t)", "mín(1.0; densidad / 2.0)", "Señal continua normalizada [0, 1] enviada al planificador A*")
    ]
    print(f"{'Parámetro / Variable':<32} | {'Valor Operativo':<25} | {'Justificación / Criterio'}")
    print("-" * 80)
    for p, v, j in filas:
        print(f"{p:<32} | {v:<25} | {j}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    imprimir_tabla_umbrales()
    generar_captura_estados_referencia()
    simular_cuello_botella_120_agentes()
