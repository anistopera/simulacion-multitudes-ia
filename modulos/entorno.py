import json
from pathlib import Path
import numpy as np


class Entorno:
    """Escenario 2D: coordenadas en metros, mapa[fila, columna]."""

    def __init__(self, ancho=30, alto=20, tam_celda=1, paso_principal=2,
                 paso_alternativo=3, configuracion=None):
        if configuracion is not None:
            datos = json.loads(Path(configuracion).read_text(encoding='utf-8'))
            ancho = datos.get('ancho', ancho)
            alto = datos.get('alto', alto)
            tam_celda = datos.get('tam_celda', tam_celda)
            paso_principal = datos.get('paso_principal', paso_principal)
            paso_alternativo = datos.get('paso_alternativo', paso_alternativo)
        else:
            datos = {}
        if tam_celda <= 0 or ancho <= 0 or alto <= 0:
            raise ValueError('Dimensiones y tamaño de celda deben ser positivos')
        if ancho % tam_celda or alto % tam_celda:
            raise ValueError('Las dimensiones deben ser múltiplos del tamaño de celda')
        if paso_principal <= 0 or paso_alternativo <= 0:
            raise ValueError('Los pasos deben tener ancho positivo')
        if paso_principal % tam_celda or paso_alternativo % tam_celda:
            raise ValueError('Los anchos de paso deben ser múltiplos del tamaño de celda')
        self.ancho, self.alto, self.tam_celda = ancho, alto, tam_celda
        self.paso_principal, self.paso_alternativo = paso_principal, paso_alternativo
        self.columnas, self.filas = int(ancho / tam_celda), int(alto / tam_celda)
        self.entrada = tuple(datos.get('entrada', [1, 11]))
        self.salida = tuple(datos.get('salida', [29, 11]))
        self.destino = self.salida
        self.mapa = np.zeros((self.filas, self.columnas), dtype=np.uint8)
        self.crear_escenario()
        for x, y in datos.get('obstaculos_extra', []):
            if not self.agregar_obstaculo(x, y):
                raise ValueError(f'Obstáculo fuera del escenario: {(x, y)}')
        if not self.es_transitable(*self.entrada) or not self.es_transitable(*self.salida):
            raise ValueError('Entrada o salida bloqueada o fuera del escenario')

    def crear_escenario(self):
        self.mapa.fill(0)
        columna = int(15 / self.tam_celda)
        if not 0 <= columna < self.columnas:
            raise ValueError('El escenario debe incluir la barrera x=15')
        pasos = [(10, 10 + self.paso_principal),
                 (4, 4 + self.paso_alternativo)]
        if any(a < 0 or b > self.alto for a, b in pasos) or pasos[1][1] > pasos[0][0]:
            raise ValueError('Los pasos se salen del recinto o se superponen')
        for fila in range(self.filas):
            y = (fila + 0.5) * self.tam_celda
            if not any(a <= y < b for a, b in pasos):
                self.mapa[fila, columna] = 1

    def obtener_celda(self, x, y):
        if not (0 <= x < self.ancho and 0 <= y < self.alto):
            return None
        return int(y / self.tam_celda), int(x / self.tam_celda)

    def es_transitable(self, x, y):
        celda = self.obtener_celda(x, y)
        return celda is not None and bool(self.mapa[celda] == 0)

    def obstaculos(self):
        """Arreglo NumPy de celdas [fila, columna] bloqueadas."""
        return np.argwhere(self.mapa == 1)

    def agregar_obstaculo(self, x, y):
        celda = self.obtener_celda(x, y)
        if celda is None or (x, y) in (self.entrada, self.salida):
            return False
        self.mapa[celda] = 1
        return True

    def quitar_obstaculo(self, x, y):
        celda = self.obtener_celda(x, y)
        if celda is None:
            return False
        self.mapa[celda] = 0
        return True

    def obtener_mapa(self):
        return self.mapa.copy()

    def dibujar_mapa(self, archivo='capturas/mapa_escenario.png', mostrar=True):
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        fig, ax = plt.subplots(figsize=(11, 7))
        ax.imshow(self.mapa, origin='lower', extent=(0, self.ancho, 0, self.alto),
                  cmap=ListedColormap(['#E8F5E9', '#37474F']), vmin=0, vmax=1,
                  interpolation='nearest')
        ax.scatter(*self.entrada, color='blue', marker='>', s=120, label='Entrada')
        ax.scatter(*self.salida, color='orange', marker='*', s=170, label='Salida')
        ax.text(16.2, 11, f'Paso principal: {self.paso_principal} m', fontsize=10)
        ax.text(16.2, 5, f'Ruta alternativa: {self.paso_alternativo} m', fontsize=10)
        ax.set(title='Escenario de simulación de multitudes', xlabel='Ancho (m)', ylabel='Alto (m)',
               xlim=(0, self.ancho), ylim=(0, self.alto))
        ax.set_xticks(np.arange(0, self.ancho + 1, 2))
        ax.set_yticks(np.arange(0, self.alto + 1, 2))
        ax.grid(alpha=0.2)
        ax.legend(loc='upper right')
        destino = Path(archivo)
        destino.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destino, dpi=200, bbox_inches='tight')
        if mostrar:
            plt.show()
        plt.close(fig)
        return destino
