"""Integración y experimentos reproducibles de simulación de multitudes.

Ejemplos desde la raíz:
    python main.py --modo B --agentes 120 --semilla 42
    python main.py --modo B --agentes 40 --semilla 42 --visualizar
    python main.py --experimentos
"""

import argparse
import csv
import json
import math
from pathlib import Path
import sys

import numpy as np

from modulos.agentes import MotorAgentes, generar_agentes
from modulos.dbscan_deteccion import detectar_grupos
from modulos.diagnostico import DiagnosticoCongestion, ESTADO_CRITICA
from modulos.entorno import Entorno
from modulos.navegacion_astar import NavegadorAdaptativo
from modulos.telemetria import Telemetria


CARPETA = Path(__file__).resolve().parent
CAPTURAS = CARPETA / 'capturas'
DT = 0.1
HORIZONTE = 180.0
ESCENARIOS = {'S1': 40, 'S2': 80, 'S3': 120}
SEMILLAS = (42, 43, 44)
MODOS_V3 = ('A', 'B', 'B_PSO')
METRICAS_COMPARADAS = ('tiempo_transito', 'tiempo_espera', 'tasa_finalizacion_pct',
                       'solapamientos', 'celdas_criticas_max', 'cambios_ruta')


def guardar_csv(ruta, filas):
    """Guarda diccionarios con su orden de columnas y precisión original."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not filas:
        raise ValueError('Se requiere al menos una fila para definir el encabezado')
    with ruta.open('w', newline='', encoding='utf-8') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


def _crear_visualizacion(entorno, carpeta_capturas, modo):
    # Importación diferida: las corridas sin interfaz no requieren SDL/Pygame.
    import pygame
    from modulos.visualizacion import Visualizacion

    return (Visualizacion(entorno, carpeta_capturas=carpeta_capturas,
                          titulo=f'Multitudes: modo {modo}'), pygame.time.Clock())


def validar_theta(datos):
    if isinstance(datos, dict):
        datos = [datos[k] for k in ('alpha', 'ks', 'kr')]
    if not isinstance(datos, (list, tuple)) or len(datos) != 3:
        raise ValueError('theta debe contener [alpha, ks, kr]')
    try:
        alpha, ks, kr = map(float, datos)
    except (TypeError, ValueError) as exc:
        raise ValueError('theta debe contener tres números') from exc
    if not all(map(math.isfinite, (alpha, ks, kr))):
        raise ValueError('theta contiene valores no finitos')
    if not (0 <= alpha <= 5 and 0.5 <= ks <= 2 and 0.5 <= kr <= 3):
        raise ValueError('theta fuera de rangos: alpha [0,5], ks [0.5,2], kr [0.5,3]')
    return alpha, ks, kr


def cargar_theta(ruta=CAPTURAS / 'theta_optimo.json'):
    """Lee parámetros calibrados; no sustituye una calibración ausente."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f'Falta calibración PSO: {ruta}. Solicítala a Keyla.')
    with ruta.open(encoding='utf-8') as archivo:
        datos = json.load(archivo)
    if isinstance(datos, dict):
        if 'theta' in datos:
            datos = datos['theta']
        elif 'theta_optimo' in datos:
            datos = datos['theta_optimo']
        else:
            datos = [datos[k] for k in ('alpha', 'ks', 'kr')]
    return validar_theta(datos)


def ejecutar_episodio(n_agentes=40, modo='A', semilla=42,
<<<<<<< HEAD
                     duracion=HORIZONTE, carpeta_salida=CAPTURAS, visualizar=False,
                     vista=None):
=======
                     duracion=HORIZONTE, carpeta_salida=CAPTURAS, visualizar=False, theta=None):
>>>>>>> origin/main
    """Ejecuta un episodio nuevo; duracion permite pruebas cortas desde Python.

    El CLI experimental siempre usa 180 s. Los no llegados se penalizan con
    ese horizonte. El cierre anticipado registra las últimas llegadas incluso
    si no coincide con un segundo entero, sin duplicar muestras. Una corrida
    visual cerrada por el usuario se marca interrumpida y calcula métricas
    al corte real; sus archivos usan el sufijo _visual y no sustituyen el lote.
    """
    modo = str(modo).upper()
    if modo not in ('A', 'B', 'B_PSO'):
        raise ValueError('Modo inválido. Use A, B o B_PSO')
    if n_agentes not in ESCENARIOS.values():
        raise ValueError('Se requieren 40, 80 o 120 agentes')
    if modo == 'B_PSO':
        alpha, ks, kr = cargar_theta() if theta is None else validar_theta(theta)
    else:
        if theta is not None:
            raise ValueError('theta solo se utiliza en B_PSO')
        alpha, ks, kr = 2.0, 1.0, 1.0
    if not math.isfinite(duracion) or duracion <= 0:
        raise ValueError('La duración debe ser finita y positiva')
    ticks = round(duracion / DT)
    if not math.isclose(ticks * DT, duracion, abs_tol=1e-9, rel_tol=0):
        raise ValueError('La duración debe ser múltiplo de 0.1 s')

    entorno = Entorno(configuracion=str(CARPETA / 'configuracion.json'))
    agentes = generar_agentes(entorno, cantidad=n_agentes, semilla=semilla)
    nav = NavegadorAdaptativo(entorno, modo='B' if modo == 'B_PSO' else modo,
                              alpha=alpha, tau=4.0, margen=0.10)
    for agente in agentes:
        if not nav.asignar_ruta_inicial(agente, t=0.0):
            raise RuntimeError(f'No existe ruta inicial para el agente {agente.id}')
    if modo == 'B_PSO':
        motor = MotorAgentes(entorno, agentes, ks=ks, kr=kr)
    else:
        motor = MotorAgentes(entorno, agentes)
    telemetria = Telemetria(entorno)
    diagnostico = DiagnosticoCongestion(entorno=entorno)
    analisis = []
    max_criticas = 0
    ultimo_tick_registrado = 0
    ticks_ejecutados = 0
    interrumpido = False
    vis = None
    if vista is not None:
        # Interfaz web (modulos/servidor_web.py): ofrece procesar_eventos, dibujar,
        # tick, conectar y cerrar. Hace de vista y de reloj a la vez.
        vis = reloj = vista
    elif visualizar:
        vis, reloj = _crear_visualizacion(entorno, carpeta_salida, modo)
    try:
        if vis is not None:
            # Calor inicial válido sin acumular persistencia ni avanzar la física.
            diagnostico.actualizar(motor.agentes_activos, dt=0.0)
        if vista is not None:
            vista.conectar(motor, diagnostico)
        for tick in range(1, ticks + 1):
            if vis is not None and not vis.procesar_eventos():
                interrumpido = True
                break
            activos = motor.actualizar(dt=DT)
            ticks_ejecutados = tick
            if tick % 10 == 0:
                telemetria.registrar(motor.tiempo, agentes, dt_muestreo=1.0)
                ultimo_tick_registrado = tick
                pos_np = telemetria.obtener_posiciones_np(activos)
                etiquetas, clusters = detectar_grupos(pos_np)
                estados, D = diagnostico.actualizar(activos, dt=1.0)
                criticas = int(np.count_nonzero(estados == ESTADO_CRITICA))
                max_criticas = max(max_criticas, criticas)
                cambios = nav.actualizar_todos(activos, motor.tiempo, D) if modo in ('B', 'B_PSO') else 0
                analisis.append({
                    't': motor.tiempo, 'activos': len(activos), 'clusters': len(clusters),
                    'agentes_ruido': int(np.count_nonzero(etiquetas == -1)),
                    'grupo_mayor': max((c['tamano'] for c in clusters), default=0),
                    'celdas_criticas': criticas,
                    'densidad_maxima': float(diagnostico.densidad.max()),
                    'cambios_ruta_instante': cambios, 'cambios_ruta_acumulados': nav.cambios,
                })
            if vis is not None:
                total_llegados = sum(a.llegado for a in agentes)
                vis.dibujar(activos, motor.tiempo, llegados=total_llegados,
                            densidad=diagnostico.densidad)
                reloj.tick(round(1 / DT))
            if not activos:
                break
    finally:
        if vis is not None:
            vis.cerrar()

    if ticks_ejecutados != ultimo_tick_registrado:
        telemetria.registrar(motor.tiempo, agentes,
                            dt_muestreo=(ticks_ejecutados - ultimo_tick_registrado) * DT)
    corte_metricas = motor.tiempo if interrumpido else duracion
    metricas = telemetria.obtener_metricas_episodio(n_agentes, corte_metricas)
    escenario = next(e for e, n in ESCENARIOS.items() if n == n_agentes)
    nombre = f'{escenario}_{modo}_semilla{semilla}'
    if visualizar or vista is not None:
        nombre += '_visual'
    carpeta_salida = Path(carpeta_salida)
    ruta_telemetria = Path('experimentos') / f'{nombre}_telemetria.csv'
    ruta_analisis = Path('experimentos') / f'{nombre}_analisis.csv'
    telemetria.exportar_csv(str(carpeta_salida / ruta_telemetria))
    if analisis:
        guardar_csv(carpeta_salida / ruta_analisis, analisis)
    return {
        'escenario': escenario, 'n_agentes': n_agentes, 'modo': modo, 'semilla': semilla,
        'horizonte_s': duracion, 'duracion_simulada_s': ticks_ejecutados * DT,
        'ticks': ticks_ejecutados, 'interrumpido': interrumpido,
        **metricas, 'tasa_finalizacion_pct': 100.0 * metricas['tasa_finalizacion'],
        'celdas_criticas_max': max_criticas, 'cambios_ruta': nav.cambios,
        'recalculos_astar': nav.recalculos, 'muestras_analisis': len(analisis),
        'filas_telemetria': len(telemetria.filas),
        'archivo_telemetria': ruta_telemetria.as_posix(),
        'archivo_analisis': ruta_analisis.as_posix() if analisis else '',
    }


def resumir_resultados(resultados, modos=('A', 'B')):
    """Promedia semillas; desviación estándar descriptiva con ddof=0.

    celdas_criticas_max promedia los máximos temporales de cada corrida.
    solapamientos promedia los totales por corrida; se conserva además su suma.
    """
    resumen = []
    for escenario, n_agentes in ESCENARIOS.items():
        for modo in modos:
            grupo = [r for r in resultados if r['escenario'] == escenario and r['modo'] == modo]
            if not grupo:
                continue
            fila = {'escenario': escenario, 'n_agentes': n_agentes, 'modo': modo,
                    'n_semillas': len(grupo)}
            for clave in METRICAS_COMPARADAS:
                valores = np.array([r[clave] for r in grupo], dtype=float)
                fila[clave] = float(valores.mean())
                fila[clave + '_std'] = float(valores.std(ddof=0))
            fila['solapamientos_suma'] = sum(r['solapamientos'] for r in grupo)
            fila['cambios_ruta_suma'] = sum(r['cambios_ruta'] for r in grupo)
            fila['celdas_criticas_pico'] = max(r['celdas_criticas_max'] for r in grupo)
            resumen.append(fila)
    return resumen


def generar_figura(resumen, ruta, modos=('A', 'B')):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ejes = plt.subplots(1, 3, figsize=(14, 5))
    colores = {'A': '#386a9b', 'B': '#d77931', 'B_PSO': '#3a9464'}
    escenarios = list(ESCENARIOS)
    x = np.arange(len(escenarios))
    especificaciones = (
        ('tiempo_transito', 'Tiempo medio de viaje', 'Segundos (no llegados: 180 s)'),
        ('tiempo_espera', 'Tiempo medio de espera', 'Segundos de bloqueo muestreado'),
        ('tasa_finalizacion_pct', 'Tasa de finalización', 'Agentes llegados (%)'),
    )
    for ax, (clave, titulo, unidad) in zip(ejes, especificaciones):
        for indice, modo in enumerate(modos):
            desplazamiento = (indice - (len(modos) - 1) / 2) * (0.8 / len(modos))
            grupo = [next(r for r in resumen if r['escenario'] == e and r['modo'] == modo)
                     for e in escenarios]
            valores = [r[clave] for r in grupo]
            barras = ax.bar(x + desplazamiento, valores, 0.8 / len(modos) * 0.9,
                            yerr=[r[clave + '_std'] for r in grupo], capsize=3,
                            color=colores[modo], label=f'Modo {modo}')
            ax.bar_label(barras, labels=[f'{v:.1f}' for v in valores], padding=4, fontsize=8)
        ax.set_xticks(x, [f'{e}\n({ESCENARIOS[e]} agentes)' for e in escenarios])
        ax.set_title(titulo)
        ax.set_ylabel(unidad)
        ax.set_ylim(bottom=0)
        ax.margins(y=.2)
        if clave == 'tasa_finalizacion_pct':
            ax.set_ylim(0, 125)
            ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_axisbelow(True)
        ax.grid(axis='y', alpha=.2)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Comparación experimental: ' + ' vs '.join(modos), fontsize=14)
    fig.legend(*ejes[0].get_legend_handles_labels(), loc='lower center', ncol=len(modos), frameon=False)
    fig.text(.5, .90, 'Semillas 42, 43 y 44 · horizonte 180 s · barras de error: desviación estándar',
             ha='center', va='top', fontsize=10)
    fig.tight_layout(rect=(0, .08, 1, .86))
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def ejecutar_experimentos(carpeta_salida=CAPTURAS):
    carpeta_salida = Path(carpeta_salida)
    resultados = []
    for escenario, n_agentes in ESCENARIOS.items():
        for modo in ('A', 'B'):
            for semilla in SEMILLAS:
                print(f'[{len(resultados) + 1}/18] {escenario}, modo {modo}, semilla {semilla}...', flush=True)
                resultado = ejecutar_episodio(n_agentes, modo, semilla, carpeta_salida=carpeta_salida)
                resultados.append(resultado)
                guardar_csv(carpeta_salida / 'resultados_experimentos.csv', resultados)
                print(f"  Viaje: {resultado['tiempo_transito']:.2f} s | "
                      f"Espera: {resultado['tiempo_espera']:.2f} s | "
                      f"Finalización: {resultado['tasa_finalizacion_pct']:.2f}% | "
                      f"Cambios: {resultado['cambios_ruta']}", flush=True)
    resumen = resumir_resultados(resultados)
    guardar_csv(carpeta_salida / 'tabla_comparativa_A_vs_B.csv', resumen)
    generar_figura(resumen, carpeta_salida / 'comparacion_experimental_A_vs_B.png')
    return resultados, resumen


def ejecutar_experimentos_v3(carpeta_salida=CAPTURAS):
    """27 episodios: 3 escenarios x 3 modos x 3 semillas."""
    carpeta_salida = Path(carpeta_salida)
    theta = cargar_theta()
    resultados = []
    for escenario, n_agentes in ESCENARIOS.items():
        for modo in MODOS_V3:
            for semilla in SEMILLAS:
                print(f'[{len(resultados) + 1}/27] {escenario}, {modo}, semilla {semilla}', flush=True)
                resultado = ejecutar_episodio(n_agentes, modo, semilla,
                    carpeta_salida=carpeta_salida,
                    theta=theta if modo == 'B_PSO' else None)
                resultados.append(resultado)
                guardar_csv(carpeta_salida / 'resultados_experimentos_v3.csv', resultados)
    resumen = resumir_resultados(resultados, modos=MODOS_V3)
    guardar_csv(carpeta_salida / 'tabla_comparativa_v3.csv', resumen)
    generar_figura(resumen, carpeta_salida / 'comparacion_experimental_A_vs_B.png', modos=MODOS_V3)
    return resultados, resumen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ejecucion = parser.add_mutually_exclusive_group()
    ejecucion.add_argument('--experimentos-v3', action='store_true', help='Comparar A/B/B_PSO (27 episodios)')
    ejecucion.add_argument('--experimentos', action='store_true', help='Ejecutar S1/S2/S3, A/B y semillas 42/43/44 (18 episodios)')
    ejecucion.add_argument('--visualizar', action='store_true', help='Mostrar la corrida individual con Pygame: H calor, S captura, Esc cerrar')
<<<<<<< HEAD
    ejecucion.add_argument('--interfaz', action='store_true', help='Abrir la interfaz web local con controles en pantalla (--modo, --agentes y --semilla fijan los valores iniciales)')
    parser.add_argument('--modo', choices=('A', 'B'), default='A')
=======
    parser.add_argument('--modo', choices=MODOS_V3, default='A')
>>>>>>> origin/main
    parser.add_argument('--agentes', type=int, choices=(40, 80, 120), default=40)
    parser.add_argument('--semilla', type=int, default=42)
    argumentos = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(argumentos)
    if not argumentos:
        parser.print_help()
        return
    if args.experimentos_v3:
        if any(a.split('=')[0] in ('--modo', '--agentes', '--semilla') for a in argumentos):
            parser.error('--experimentos-v3 no admite opciones individuales')
        ejecutar_experimentos_v3()
        print('27 episodios terminados. Resultados V3 en:', CAPTURAS)
    elif args.experimentos:
        if any(a.split('=')[0] in ('--modo', '--agentes', '--semilla') for a in argumentos):
            parser.error('--experimentos define todas las combinaciones; no combinar con opciones individuales')
        ejecutar_experimentos()
        print('18 episodios terminados. Resultados, tabla y figura en:', CAPTURAS)
    elif args.interfaz:
        from modulos import servidor_web
        escenario = next(e for e, n in ESCENARIOS.items() if n == args.agentes)
        servidor_web.servir(sys.modules[__name__], args.modo, escenario, args.semilla)
    else:
        if args.visualizar:
            resultado = ejecutar_episodio(args.agentes, args.modo, args.semilla, visualizar=True)
        else:
            resultado = ejecutar_episodio(args.agentes, args.modo, args.semilla)
        sufijo = '_visual' if args.visualizar else ''
        guardar_csv(CAPTURAS / f"resultado_{resultado['escenario']}_{args.modo}_semilla{args.semilla}{sufijo}.csv", [resultado])
        for clave, valor in resultado.items():
            print(f'{clave}: {valor}')


if __name__ == '__main__':
    main()
