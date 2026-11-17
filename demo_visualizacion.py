"""Demo integrada: movimiento de Sthaicy y rutas A* fijas de Keyla.

Datos iniciales generados para demostración. La vista no calcula movimiento.
"""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cantidad', type=int, choices=(40, 80, 120), default=40)
    parser.add_argument('--semilla', type=int, default=42)
    parser.add_argument('--sin-ventana', action='store_true')
    parser.add_argument('--frames', type=int, help='Pasos de 0.1 s; por defecto sin límite')
    parser.add_argument('--captura', type=Path)
    parser.add_argument('--calor', action='store_true')
    args = parser.parse_args()
    if args.frames is not None and args.frames <= 0:
        parser.error('--frames debe ser positivo')
    if args.sin_ventana:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        if args.frames is None:
            args.frames = 100

    import pygame
    from modulos.entorno import Entorno
    from modulos.agentes import MotorAgentes, generar_agentes
    from modulos.diagnostico import DiagnosticoCongestion
    from modulos.visualizacion import Visualizacion

    raiz = Path(__file__).resolve().parent
    entorno = Entorno(configuracion=raiz / 'configuracion.json')
    agentes = generar_agentes(entorno, args.cantidad, args.semilla)
    motor = MotorAgentes(entorno, agentes)
    diagnostico = DiagnosticoCongestion(entorno=entorno)
    vista = Visualizacion(entorno, carpeta_capturas=raiz / 'capturas',
                          titulo='DEMO integrada: agentes + A* fijo')
    vista.mostrar_calor = args.calor
    reloj = pygame.time.Clock()
    pasos = 0
    # La inicialización no acumula persistencia de congestión.
    diagnostico.actualizar(motor.agentes_activos, dt=0)
    try:
        vista.dibujar(agentes, motor.tiempo, densidad=diagnostico.densidad)
        while vista.procesar_eventos():
            motor.actualizar(dt=0.1)
            pasos += 1
            # Diagnóstico a 1 Hz simulado; la vista no altera sus matrices.
            if pasos % 10 == 0:
                diagnostico.actualizar(motor.agentes_activos, dt=1.0)
            vista.dibujar(agentes, motor.tiempo, densidad=diagnostico.densidad)
            if (args.frames is not None and pasos >= args.frames) or not motor.agentes_activos:
                break
            if not args.sin_ventana:
                reloj.tick(10)
        if args.captura:
            print('Captura:', vista.guardar_captura(args.captura))
        print(f'Tiempo simulado: {motor.tiempo:.1f} s | '
              f'Activos: {len(motor.agentes_activos)} | '
              f'Llegados: {sum(a.llegado for a in agentes)}')
    finally:
        vista.cerrar()


if __name__ == '__main__':
    main()
