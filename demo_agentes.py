"""Evidencia del movimiento de Sthaicy, sin implementar la interfaz de Wendy.

python3 demo_agentes.py --cantidad 40 --no-mostrar
python3 demo_agentes.py --cantidad 40 --no-mostrar --gif
"""
import argparse
from pathlib import Path

import numpy as np

from modulos.agentes import MotorAgentes, generar_agentes
from modulos.entorno import Entorno


CARPETA = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cantidad', type=int, choices=(40, 80, 120), default=40)
    parser.add_argument('--semilla', type=int, default=42)
    parser.add_argument('--duracion', type=int, default=60)
    parser.add_argument('--no-mostrar', action='store_true')
    parser.add_argument('--gif', action='store_true', help='Guardar también una animación GIF')
    args = parser.parse_args()
    if args.duracion < 3:
        parser.error('--duracion debe ser al menos 3 segundos')
    import matplotlib
    if args.no_mostrar:
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, Normalize
    from matplotlib.collections import EllipseCollection
    from matplotlib.animation import FuncAnimation, PillowWriter

    entorno = Entorno(configuracion=str(CARPETA / 'configuracion.json'))
    agentes = generar_agentes(entorno, args.cantidad, args.semilla)
    motor = MotorAgentes(entorno, agentes)
    fotogramas = []

    def guardar():
        fotogramas.append((motor.tiempo,
                          np.array([[a.x, a.y, a.velocidad, a.radio] for a in motor.agentes_activos]).reshape(-1, 4),
                          sum(a.llegado for a in agentes)))

    guardar()
    for paso in range(args.duracion * 10):
        motor.actualizar(0.1)
        if (paso + 1) % 10 == 0:
            guardar()

    normalizar = Normalize(0, motor.velocidad_max)
    colores = plt.get_cmap('RdYlGn')

    def dibujar(ax, fotograma):
        t, datos, llegados = fotograma
        ax.clear()
        ax.imshow(entorno.mapa, origin='lower', extent=(0, entorno.ancho, 0, entorno.alto),
                  cmap=ListedColormap(['#f3f6f8', '#37474f']), vmin=0, vmax=1,
                  interpolation='nearest')
        ax.scatter(*entorno.entrada, marker='>', c='#1565c0', s=65, label='Entrada')
        ax.scatter(*entorno.salida, marker='*', c='#f57c00', s=90, label='Salida')
        if len(datos):
            discos = EllipseCollection(2*datos[:, 3], 2*datos[:, 3], np.zeros(len(datos)),
                                      units='xy', offsets=datos[:, :2], transOffset=ax.transData,
                                      facecolors=colores(normalizar(datos[:, 2])),
                                      edgecolors='#263238', linewidths=0.35)
            ax.add_collection(discos)
        ax.set(xlim=(0, 30), ylim=(0, 20), xlabel='x (m)', ylabel='y (m)', aspect='equal',
               title=f't = {t:.0f} s | activos: {len(datos)} | llegados: {llegados}')
        ax.legend(loc='upper left', fontsize=8)

    salida = CARPETA / 'capturas'
    salida.mkdir(exist_ok=True)
    nombre = f'agentes_{args.cantidad}_semilla_{args.semilla}'
    fig, ejes = plt.subplots(2, 2, figsize=(12, 8.8), layout='constrained')
    for ax, k in zip(ejes.flat, np.linspace(0, args.duracion, 4, dtype=int)):
        dibujar(ax, fotogramas[k])
    fig.suptitle(f'Movimiento por fuerzas y rutas A* fijas | {args.cantidad} agentes | semilla {args.semilla}')
    barra = fig.colorbar(plt.cm.ScalarMappable(norm=normalizar, cmap=colores), ax=ejes, shrink=0.8)
    barra.set_label('Velocidad (m/s)')
    png = salida / f'{nombre}.png'
    fig.savefig(png, dpi=160)
    print(f'Capturas: {png}')
    if args.gif:
        anim_fig, ax = plt.subplots(figsize=(8, 5.5), layout='constrained')
        anim = FuncAnimation(anim_fig, lambda k: dibujar(ax, fotogramas[k]),
                             frames=len(fotogramas), interval=100, repeat=False)
        gif = salida / f'{nombre}.gif'
        anim.save(gif, writer=PillowWriter(fps=10), dpi=100)
        plt.close(anim_fig)
        print(f'Animación: {gif}')
    print(f'Tiempo simulado: {motor.tiempo:.1f} s | Activos: {len(motor.agentes_activos)} | '
          f'Llegados: {sum(a.llegado for a in agentes)}/{len(agentes)}')
    print('Demostración del motor con rutas fijas; no es una comparación de rendimiento A/B.')
    if not args.no_mostrar:
        plt.show()
    plt.close(fig)


if __name__ == '__main__':
    main()
