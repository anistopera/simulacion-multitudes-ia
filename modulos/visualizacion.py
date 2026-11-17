"""Vista de solo lectura. Metros (x, y), origen inferior izquierdo.

La densidad externa se expresa en personas/m², matriz [fila, columna]
de celdas de 2 m. Si se omite, se calcula contando agentes activos.
"""
from dataclasses import dataclass
from datetime import datetime
from math import ceil, hypot, isfinite
from pathlib import Path

import numpy as np
import pygame


@dataclass(frozen=True)
class AgenteVisual:
    """Instantánea: rapidez escalar en m/s (usar la norma si es vector)."""

    posicion: tuple[float, float]
    velocidad_actual: float
    velocidad_deseada: float
    llegado: bool = False
    radio: float = 0.25
    activo: bool = True

    def __post_init__(self):
        if len(self.posicion) != 2 or not all(isfinite(v) for v in self.posicion):
            raise ValueError('La posición debe contener dos números finitos')
        if not all(isfinite(v) and v >= 0 for v in
                   (self.velocidad_actual, self.velocidad_deseada)):
            raise ValueError('Las velocidades deben ser finitas y no negativas')
        if not isfinite(self.radio) or self.radio <= 0:
            raise ValueError('El radio debe ser finito y positivo')

    @classmethod
    def desde_agente(cls, agente):
        """Copia la interfaz de Sthaicy sin modificar ni retener su estado.

        `activo` y `llegado` son opcionales para la interfaz inicial acordada.
        No se deduce llegada a partir de la posición o la velocidad.
        """
        if isinstance(agente, cls):
            return agente
        return cls((agente.x, agente.y), hypot(agente.vx, agente.vy),
                   agente.v_deseada, llegado=getattr(agente, 'llegado', False),
                   radio=agente.radio, activo=getattr(agente, 'activo', True))


def color_velocidad(actual, deseada):
    """Rojo: detenido; amarillo: mitad; verde: velocidad deseada o mayor.

    Deseada cero: gris, ya que el cociente no está definido.
    """
    if deseada == 0:
        return (130, 140, 150)
    proporcion = max(0.0, min(1.0, actual / deseada))
    return (round(230 * min(1, 2 * (1 - proporcion))),
            round(200 * min(1, 2 * proporcion)), 55)


class Visualizacion:
    def __init__(self, entorno, pixeles_por_metro=28, carpeta_capturas='capturas',
                 titulo='Simulación de multitudes'):
        if not isfinite(pixeles_por_metro) or pixeles_por_metro < 4:
            raise ValueError('La escala debe ser al menos 4 píxeles por metro')
        self.entorno = entorno
        self.escala = pixeles_por_metro
        self.margen = 32
        self.ancho = round(entorno.ancho * self.escala)
        self.alto = round(entorno.alto * self.escala)
        self.carpeta_capturas = Path(carpeta_capturas)
        self.mostrar_calor = False
        self.ultima_captura = None
        self._captura_pendiente = False
        pygame.display.init()
        pygame.font.init()
        self.pantalla = pygame.display.set_mode(
            (self.ancho + 2 * self.margen + 340,
             max(self.alto + 2 * self.margen, 600)))
        pygame.display.set_caption(titulo)
        self.fuente = pygame.font.Font(None, 23)
        self.titulo = titulo

    def a_pantalla(self, x, y):
        return (self.margen + round(x * self.escala),
                self.margen + self.alto - round(y * self.escala))

    def rectangulo(self, x, y, ancho, alto):
        izquierda, arriba = self.a_pantalla(x, y + alto)
        derecha, abajo = self.a_pantalla(x + ancho, y)
        return pygame.Rect(izquierda, arriba, derecha - izquierda, abajo - arriba)

    def densidad_agentes(self, agentes):
        e = self.entorno
        densidad = np.zeros((ceil(e.alto / 2), ceil(e.ancho / 2)))
        for agente in agentes:
            agente = AgenteVisual.desde_agente(agente)
            x, y = agente.posicion
            if agente.activo and not agente.llegado and 0 <= x < e.ancho and 0 <= y < e.alto:
                densidad[int(y / 2), int(x / 2)] += 1
        # También respeta el área de las celdas parciales del borde.
        areas = np.outer(np.minimum(2, e.alto - np.arange(densidad.shape[0]) * 2),
                         np.minimum(2, e.ancho - np.arange(densidad.shape[1]) * 2))
        return densidad / areas

    def procesar_eventos(self, eventos=None):
        """False indica cierre. Acepta los eventos ya leídos por el motor.

        Si se omiten, consume la cola de Pygame. Llamar en el hilo principal.
        """
        continuar = True
        for evento in pygame.event.get() if eventos is None else eventos:
            if evento.type == pygame.QUIT:
                continuar = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    continuar = False
                elif evento.key == pygame.K_h:
                    self.mostrar_calor = not self.mostrar_calor
                elif evento.key == pygame.K_s:
                    self._captura_pendiente = True
        return continuar

    def dibujar(self, agentes, tiempo_simulado, llegados=None, densidad=None):
        """Dibuja una instantánea sin avanzar el motor.

        `llegados` permite pasar el total acumulado si el motor retira agentes.
        El tiempo es proporcionado por el motor, en segundos simulados.
        """
        agentes = tuple(AgenteVisual.desde_agente(a) for a in agentes)
        if not isfinite(tiempo_simulado) or tiempo_simulado < 0:
            raise ValueError('Tiempo simulado inválido')
        if llegados is None:
            llegados = sum(a.llegado for a in agentes)
        if not isinstance(llegados, (int, np.integer)) or llegados < 0:
            raise ValueError('Llegados debe ser un entero no negativo')
        e = self.entorno
        if densidad is None:
            densidad = self.densidad_agentes(agentes)
        densidad = np.asarray(densidad, dtype=float)
        if (densidad.shape != (ceil(e.alto / 2), ceil(e.ancho / 2))
                or not np.isfinite(densidad).all() or (densidad < 0).any()):
            raise ValueError('Densidad inválida: se espera [fila, columna] en celdas de 2 m')
        self.pantalla.fill((20, 28, 39))
        recinto = self.rectangulo(0, 0, e.ancho, e.alto)
        pygame.draw.rect(self.pantalla, (233, 239, 238), recinto)
        if self.mostrar_calor:
            for (fila, columna), valor in np.ndenumerate(densidad):
                intensidad = min(1, valor / 4.0)
                color = (255, round(245 - 195 * intensidad),
                         round(220 - 175 * intensidad))
                pygame.draw.rect(self.pantalla, color, self.rectangulo(
                    columna * 2, fila * 2, min(2, e.ancho - columna * 2),
                    min(2, e.alto - fila * 2)))
        for fila, columna in e.obstaculos():
            pygame.draw.rect(self.pantalla, (57, 70, 83), self.rectangulo(
                columna * e.tam_celda, fila * e.tam_celda, e.tam_celda, e.tam_celda))
        pygame.draw.rect(self.pantalla, (105, 125, 140), recinto, 2)
        for posicion, color in ((e.entrada, (35, 125, 235)), (e.salida, (170, 65, 210))):
            pygame.draw.circle(self.pantalla, color, self.a_pantalla(*posicion),
                               max(5, round(self.escala * .45)), 3)
        for agente in agentes:
            x, y = agente.posicion
            if agente.activo and not agente.llegado and 0 <= x < e.ancho and 0 <= y < e.alto:
                pygame.draw.circle(self.pantalla,
                                   color_velocidad(agente.velocidad_actual, agente.velocidad_deseada),
                                   self.a_pantalla(x, y), max(1, round(self.escala * agente.radio)))
        activos = sum(a.activo and not a.llegado for a in agentes)
        lineas = [self.titulo, '', f'Activos: {activos}',
                  f'Llegados: {llegados}', f'Tiempo simulado: {tiempo_simulado:.1f} s', '',
                  'Color: rapidez / deseada', 'Rojo 0 | amarillo 0.5 | verde 1+',
                  'Gris: deseada = 0', '', 'Azul: entrada | violeta: salida',
                  f'H: calor {"ON" if self.mostrar_calor else "OFF"}',
                  'Calor: 0 claro a 4+ rojo (pers/m²)', 'Celdas de densidad: 2 x 2 m',
                  'S: guardar PNG | Esc: cerrar', '', '(0, 0): abajo a la izquierda']
        if self.ultima_captura is not None:
            lineas.append('PNG guardado en carpeta de capturas')
        for indice, texto in enumerate(lineas):
            self.pantalla.blit(self.fuente.render(texto, True, (225, 234, 243)),
                               (self.ancho + 2 * self.margen, self.margen + indice * 27))
        pygame.display.flip()
        if self._captura_pendiente:
            self.guardar_captura()
            self._captura_pendiente = False

    def guardar_captura(self, archivo=None):
        destino = Path(archivo) if archivo else self.carpeta_capturas / (
            f'visualizacion_{datetime.now():%Y%m%d_%H%M%S_%f}.png')
        destino.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(self.pantalla, str(destino))
        self.ultima_captura = destino
        return destino

    def cerrar(self):
        pygame.display.quit()
        pygame.font.quit()
