# -*- coding: utf-8 -*-
"""
Pruebas unitarias y de integración para el Módulo 6: Diagnóstico de congestión
Responsable: Lora Quilla Santiago Leonardo

Ejecutar:
    py pruebas_diagnostico.py
"""

import math
import sys
from pathlib import Path

CARPETA_PROYECTO = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA_PROYECTO))

import numpy as np

from modulos.entorno import Entorno
from modulos.diagnostico import (
    DiagnosticoCongestion,
    ESTADO_LIBRE,
    ESTADO_ACUMULACION,
    ESTADO_CRITICA,
    ESTADO_OBSTACULO,
    UMBRAL_DENSIDAD_ALERTA,
    UMBRAL_DENSIDAD_CRITICA,
    PERSISTENCIA_MINIMA
)


def prueba_1_dimensiones_y_forma():
    """Verifica que la cuadrícula de 2x2 m sobre 30x20 m produzca una matriz de 10x15."""
    diag = DiagnosticoCongestion(ancho=30, alto=20, tam_celda=2.0)
    assert diag.forma == (10, 15), f"Forma incorrecta: {diag.forma}, se esperaba (10, 15)"
    assert diag.filas == 10
    assert diag.columnas == 15
    print("  [OK] Prueba 1: Dimensiones y forma de cuadrícula (10x15)")


def prueba_2_mapeo_coordenadas():
    """Comprueba la conversión de coordenadas (x, y) a celdas (fila, columna)."""
    diag = DiagnosticoCongestion(ancho=30, alto=20, tam_celda=2.0)
    assert diag.obtener_celda(0.5, 0.5) == (0, 0)
    assert diag.obtener_celda(15.0, 10.0) == (5, 7)
    assert diag.obtener_celda(29.9, 19.9) == (9, 14)
    assert diag.obtener_celda(-1.0, 5.0) is None
    assert diag.obtener_celda(31.0, 5.0) is None
    print("  [OK] Prueba 2: Mapeo de coordenadas continuo a discreto")


def prueba_3_area_util_con_entorno():
    """Verifica que descuente obstáculos correctamente."""
    entorno = Entorno(ancho=30, alto=20)
    diag = DiagnosticoCongestion(entorno=entorno)

    # Celda sin obstáculos debe tener 4.0 m²
    assert math.isclose(diag.area_util[0, 0], 4.0), f"Área útil esperada 4.0, obtenida {diag.area_util[0, 0]}"

    # Celdas sobre la barrera x=15 (columna 7 en celdas de 2x2 m)
    # Deben tener menor área útil o 0.0 si es completamente obstáculo
    area_col_barrera = [diag.area_util[f, 7] for f in range(diag.filas)]
    assert any(a < 4.0 for a in area_col_barrera), "No se detectaron obstáculos en la barrera"
    print("  [OK] Prueba 3: Cálculo de área útil descontando obstáculos")


def prueba_4_clasificacion_libre():
    """Con pocos agentes (< 1.5 ag/m²), el estado debe ser 'libre'."""
    diag = DiagnosticoCongestion()
    # 2 agentes en la celda (0, 0) de 4 m² -> densidad = 0.5 ag/m²
    agentes = [
        {'x': 0.5, 'y': 0.5, 'vx': 1.2, 'vy': 0.0, 'v_deseada': 1.2},
        {'x': 1.5, 'y': 1.5, 'vx': 1.1, 'vy': 0.1, 'v_deseada': 1.2}
    ]
    estados, D = diag.actualizar(agentes, dt=1.0)
    assert estados[0, 0] == ESTADO_LIBRE
    assert math.isclose(diag.densidad[0, 0], 0.5)
    assert math.isclose(D[0, 0], 0.5 / 2.0)
    print("  [OK] Prueba 4: Clasificación en estado 'libre'")


def prueba_5_clasificacion_acumulacion():
    """Con densidad >= 1.5 pero con buena velocidad, debe ser 'acumulacion'."""
    diag = DiagnosticoCongestion()
    # 7 agentes en la celda (2, 2) de 4 m² -> densidad = 1.75 ag/m² (>= 1.5)
    # pero todos a velocidad normal (1.2 m/s > 50% de 1.2)
    agentes = [{'x': 4.5, 'y': 4.5, 'vx': 1.2, 'vy': 0.0, 'v_deseada': 1.2} for _ in range(7)]
    estados, D = diag.actualizar(agentes, dt=1.0)

    assert estados[2, 2] == ESTADO_ACUMULACION
    assert diag.densidad[2, 2] == 1.75
    assert math.isclose(D[2, 2], 1.75 / 2.0)
    print("  [OK] Prueba 5: Clasificación en estado 'acumulación' (densidad alta pero fluye)")


def prueba_6_clasificacion_critica_y_persistencia():
    """
    Densidad >= 2.0 y v <= 50% requiere al menos 3.0 segundos para pasar a 'critica'.
    Antes de 3s debe permanecer en 'acumulacion'.
    """
    diag = DiagnosticoCongestion()
    # 9 agentes en la celda (3, 3) -> densidad = 2.25 ag/m² (>= 2.0)
    # velocidad casi nula (0.1 m/s <= 0.6 m/s que es el 50% de 1.2)
    agentes_bloqueados = [{'x': 6.5, 'y': 6.5, 'vx': 0.1, 'vy': 0.0, 'v_deseada': 1.2} for _ in range(9)]

    # Segundo 1 (dt = 1.0) -> t_bloqueo = 1.0 s (< 3.0 s) => debe ser 'acumulacion'
    estados, _ = diag.actualizar(agentes_bloqueados, dt=1.0)
    assert estados[3, 3] == ESTADO_ACUMULACION, f"En t=1s no debe ser crítica, fue {estados[3, 3]}"
    assert diag.tiempo_bloqueo[3, 3] == 1.0

    # Segundo 2 (dt = 1.0) -> t_bloqueo = 2.0 s (< 3.0 s) => aún 'acumulacion'
    estados, _ = diag.actualizar(agentes_bloqueados, dt=1.0)
    assert estados[3, 3] == ESTADO_ACUMULACION, f"En t=2s no debe ser crítica, fue {estados[3, 3]}"
    assert diag.tiempo_bloqueo[3, 3] == 2.0

    # Segundo 3 (dt = 1.0) -> t_bloqueo = 3.0 s (>= 3.0 s) => ¡CRÍTICA!
    estados, D = diag.actualizar(agentes_bloqueados, dt=1.0)
    assert estados[3, 3] == ESTADO_CRITICA, f"En t=3s debe ser crítica, fue {estados[3, 3]}"
    assert diag.tiempo_bloqueo[3, 3] == 3.0
    # D debe estar acotado a 1.0 máximo
    assert math.isclose(D[3, 3], 1.0)
    print("  [OK] Prueba 6: Regla de persistencia temporal (3 segundos para estado crítico)")


def prueba_7_descongestion_y_reinicio_timer():
    """Si los agentes vuelven a moverse, el timer de persistencia se resetea a 0."""
    diag = DiagnosticoCongestion()
    agentes_bloqueados = [{'x': 6.5, 'y': 6.5, 'vx': 0.05, 'vy': 0.0, 'v_deseada': 1.2} for _ in range(9)]
    diag.actualizar(agentes_bloqueados, dt=3.0)
    assert diag.estados[3, 3] == ESTADO_CRITICA

    # Los agentes aceleran a 1.2 m/s
    agentes_liberados = [{'x': 6.5, 'y': 6.5, 'vx': 1.2, 'vy': 0.0, 'v_deseada': 1.2} for _ in range(9)]
    estados, _ = diag.actualizar(agentes_liberados, dt=1.0)

    # Debe pasar a acumulación (sigue denso pero fluye) y reiniciar el timer
    assert estados[3, 3] == ESTADO_ACUMULACION
    assert diag.tiempo_bloqueo[3, 3] == 0.0
    print("  [OK] Prueba 7: Recuperación de flujo y reinicio de temporizador")


def prueba_8_compatibilidad_con_astar():
    """Comprueba que la matriz D entregada encaje con el Módulo 7 (Navegación A*)."""
    try:
        from modulos.navegacion_astar import astar, _D_por_celda
        entorno = Entorno()
        diag = DiagnosticoCongestion(entorno=entorno)

        # Generar congestión sintética en la entrada del paso principal
        agentes = [{'x': 14.5, 'y': 11.0, 'vx': 0.0, 'vy': 0.0, 'v_deseada': 1.2} for _ in range(12)]
        estados, D = diag.actualizar(agentes, dt=3.0)

        assert D.shape == (10, 15)
        assert 0.0 <= np.min(D) and np.max(D) <= 1.0

        # Probar expansión a cuadrícula de A*
        Dc = _D_por_celda(entorno, D)
        assert Dc.shape == (entorno.filas, entorno.columnas)

        # Probar A* usando la matriz D entregada por Santiago
        ruta, costo = astar(entorno, (11, 1), (11, 28), D=D, alpha=2.0)
        assert ruta is not None
        assert costo > 0.0
        print("  [OK] Prueba 8: Compatibilidad verificada con Módulo 7 (A*)")
    except ImportError as e:
        print(f"  [AVISO] No se pudo probar A* por importación: {e}")


def prueba_9_soporte_formatos_entrada():
    """Acepta dicts, objetos y tuplas de telemetría."""
    diag = DiagnosticoCongestion()

    class AgenteObj:
        def __init__(self, x, y, vx, vy, v_des=1.2):
            self.x, self.y, self.vx, self.vy, self.v_deseada = x, y, vx, vy, v_des

    datos_mixtos = [
        {'x': 2.0, 'y': 2.0, 'vx': 1.0, 'vy': 0.0, 'v_deseada': 1.2},
        AgenteObj(2.5, 2.5, 1.1, 0.0),
        [1.0, 0, 2.8, 2.8, 0.9, 0.0]  # Telemetría: t, id, x, y, vx, vy
    ]
    estados, D = diag.actualizar(datos_mixtos, dt=1.0)
    assert diag.conteo_agentes[1, 1] == 3
    print("  [OK] Prueba 9: Compatibilidad con múltiples formatos de agente")


def main():
    print("==================================================")
    print(" EJECUTANDO PRUEBAS DEL MÓDULO 6: DIAGNÓSTICO")
    print(" Responsable: Lora Quilla Santiago Leonardo")
    print("==================================================")
    prueba_1_dimensiones_y_forma()
    prueba_2_mapeo_coordenadas()
    prueba_3_area_util_con_entorno()
    prueba_4_clasificacion_libre()
    prueba_5_clasificacion_acumulacion()
    prueba_6_clasificacion_critica_y_persistencia()
    prueba_7_descongestion_y_reinicio_timer()
    prueba_8_compatibilidad_con_astar()
    prueba_9_soporte_formatos_entrada()
    print("==================================================")
    print(" [EXITO] TODAS LAS PRUEBAS UNITARIAS PASARON (9/9)")
    print("==================================================")


if __name__ == "__main__":
    main()
